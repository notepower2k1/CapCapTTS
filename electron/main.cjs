const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const https = require('https');
const net = require('net');
const path = require('path');

const DEFAULT_MODE = process.env.CAPCAP_DEFAULT_MODE || 'gpu';
const VALID_MODES = new Set(['cpu', 'gpu']);
let backendProcess = null;
let mainWindow = null;
let backendUrl = null;

function getMode() {
  const modeArg = process.argv.find((arg) => arg === '--mode=cpu' || arg === '--mode=gpu');
  const mode = modeArg ? modeArg.split('=')[1] : DEFAULT_MODE;
  return VALID_MODES.has(mode) ? mode : DEFAULT_MODE;
}

function appRoot() {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..');
}

function getAppIcon() {
  const root = appRoot();
  const candidates = [
    path.join(root, 'frontend', 'capcap.ico'),
    path.join(root, 'frontend', 'capcap.png'),
    path.join(__dirname, '..', 'frontend', 'capcap.ico'),
    path.join(__dirname, '..', 'frontend', 'capcap.png'),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || undefined;
}

function firstExisting(paths, fallback) {
  return paths.find((candidate) => fs.existsSync(candidate)) || fallback;
}

function runtimeDir(mode) {
  return path.join(app.getPath('userData'), 'runtime', mode, app.getVersion());
}

function bundledPython(mode, root) {
  const portableName = mode === 'cpu' ? 'python-portable-cpu' : 'python-portable';
  const candidate = path.join(root, portableName, 'python.exe');
  return fs.existsSync(candidate) ? candidate : null;
}

function updateSetupWindow(setupWindow, message, progress = null) {
  if (!setupWindow || setupWindow.isDestroyed()) return;
  const safeMessage = JSON.stringify(message);
  const safeProgress = progress === null ? 'null' : String(Math.max(0, Math.min(100, progress)));
  setupWindow.webContents.executeJavaScript(
    `window.capcapSetupUpdate(${safeMessage}, ${safeProgress})`,
  ).catch(() => {});
}

function createSetupWindow(mode) {
  const setupWindow = new BrowserWindow({
    width: 560,
    height: 340,
    resizable: false,
    show: false,
    icon: getAppIcon(),
    title: `CapCap TTS ${mode.toUpperCase()} - setup`,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  const html = `<!doctype html><meta charset="utf-8"><title>CapCap TTS setup</title>
    <style>body{font:14px Segoe UI,sans-serif;background:#221f1a;color:#eee8df;padding:28px}
    h2{font-weight:500;margin:0 0 18px}#msg{min-height:46px;line-height:1.5;color:#d7c9b8}
    .bar{height:8px;background:#4a4237;border-radius:8px;overflow:hidden;margin:20px 0}
    #fill{height:100%;width:0;background:#c99a61;transition:width .2s}
    #log{font:12px Consolas,monospace;color:#9f968b;white-space:nowrap;overflow:hidden}</style>
    <h2>Preparing CapCap TTS ${mode.toUpperCase()}</h2><div id="msg">Checking runtime...</div>
    <div class="bar"><div id="fill"></div></div><div id="log">This may take a few minutes on first run.</div>
    <script>window.capcapSetupUpdate=(m,p)=>{document.getElementById('msg').textContent=m;document.getElementById('log').textContent=m;if(p!==null)document.getElementById('fill').style.width=p+'%'};</script>`;
  const ready = setupWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`)
    .then(() => setupWindow.show());
  return { setupWindow, ready };
}

function downloadFile(url, destination, onProgress) {
  return new Promise((resolve, reject) => {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    const request = (currentUrl, redirectCount = 0) => {
      if (redirectCount > 5) return reject(new Error('Too many download redirects.'));
      const client = currentUrl.startsWith('https:') ? https : http;
      const req = client.get(currentUrl, { headers: { 'User-Agent': 'CapCap-TTS-Setup' } }, (response) => {
        if ([301, 302, 303, 307, 308].includes(response.statusCode) && response.headers.location) {
          response.resume();
          return request(new URL(response.headers.location, currentUrl).toString(), redirectCount + 1);
        }
        if (response.statusCode !== 200) {
          response.resume();
          return reject(new Error(`Download failed (${response.statusCode}): ${currentUrl}`));
        }
        const total = Number(response.headers['content-length'] || 0);
        let received = 0;
        const file = fs.createWriteStream(destination);
        response.on('data', (chunk) => {
          received += chunk.length;
          onProgress?.(received, total);
        });
        response.pipe(file);
        file.on('finish', () => file.close(resolve));
        file.on('error', (error) => {
          file.close(() => {});
          fs.rmSync(destination, { force: true });
          reject(error);
        });
      });
      req.on('error', reject);
    };
    request(url);
  });
}

function runCommand(command, args, options, onOutput) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { ...options, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    const collect = (chunk) => {
      output = (output + chunk.toString()).slice(-4000);
      onOutput?.(chunk.toString());
    };
    child.stdout.on('data', collect);
    child.stderr.on('data', collect);
    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} exited with code ${code}.\n${output}`));
    });
  });
}

function psQuote(value) {
  return `'${value.replace(/'/g, "''")}'`;
}

async function ensureRuntime(mode, setupWindow) {
  const root = appRoot();
  const dir = runtimeDir(mode);
  const python = path.join(dir, 'python.exe');
  const marker = path.join(dir, `.ready-${app.getVersion()}`);
  if (fs.existsSync(python) && fs.existsSync(marker)) return python;

  if (fs.existsSync(dir)) fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const pythonZip = path.join(dir, 'python-embed.zip');
  const pipScript = path.join(dir, 'get-pip.py');
  const embeddedZip = path.join(root, 'python-embed.zip');
  const pythonUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip';
  const pipUrl = 'https://bootstrap.pypa.io/get-pip.py';

  if (fs.existsSync(embeddedZip)) {
    updateSetupWindow(setupWindow, 'Extracting embedded Python...', 30);
    fs.copyFileSync(embeddedZip, pythonZip);
  } else {
    updateSetupWindow(setupWindow, 'Downloading embedded Python...', 0);
    await downloadFile(pythonUrl, pythonZip, (received, total) => {
      updateSetupWindow(setupWindow, `Downloading Python (${Math.round(received / 1024 / 1024)} MB)`, total ? received * 30 / total : null);
    });
  }
  updateSetupWindow(setupWindow, 'Extracting Python runtime...', 32);
  const ps = process.platform === 'win32' ? 'powershell.exe' : 'powershell';
  await runCommand(ps, ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command',
    `Expand-Archive -LiteralPath ${psQuote(pythonZip)} -DestinationPath ${psQuote(dir)} -Force`]);
  fs.rmSync(pythonZip, { force: true });
  fs.writeFileSync(path.join(dir, 'python311._pth'), 'python311.zip\n.\nLib\\site-packages\n\nimport site\n');

  updateSetupWindow(setupWindow, 'Installing pip...', 38);
  await downloadFile(pipUrl, pipScript, (received, total) => {
    updateSetupWindow(setupWindow, 'Downloading pip...', total ? 38 + received * 8 / total : null);
  });
  await runCommand(python, [pipScript], { cwd: dir, env: process.env }, (line) => updateSetupWindow(setupWindow, line.trim().slice(-180)));
  fs.rmSync(pipScript, { force: true });

  const requirements = path.join(root, mode === 'cpu' ? 'backend_cpu' : 'backend', 'requirements.txt');
  const pipArgs = ['-m', 'pip', 'install', '--no-cache-dir', '--disable-pip-version-check', '-r', requirements];
  if (mode === 'gpu') {
    updateSetupWindow(setupWindow, 'Installing GPU PyTorch/CUDA runtime...', 50);
    await runCommand(python, ['-m', 'pip', 'install', '--no-cache-dir', '--disable-pip-version-check', 'torch', 'torchaudio', '--index-url', 'https://download.pytorch.org/whl/cu124'], { cwd: dir, env: process.env }, (line) => updateSetupWindow(setupWindow, line.trim().slice(-180)));
  }
  updateSetupWindow(setupWindow, 'Installing CapCap TTS libraries...', 68);
  await runCommand(python, pipArgs, { cwd: dir, env: process.env }, (line) => updateSetupWindow(setupWindow, line.trim().slice(-180)));
  fs.writeFileSync(marker, JSON.stringify({ version: app.getVersion(), mode, installedAt: new Date().toISOString() }));
  updateSetupWindow(setupWindow, 'Runtime ready. Starting CapCap TTS...', 100);
  return python;
}

function configureEnvironment(mode) {
  const root = appRoot();
  const resourceRoot = app.isPackaged ? process.resourcesPath : root;
  const dataRoot = path.join(app.getPath('userData'), mode);
  const resourceBase = path.join(root, 'models');
  const externalResource = path.resolve(root, '..', 'TTS_Resource');

  const env = {
    ...process.env,
    CAPCAP_MODE: mode,
    FFMPEG_DIR: process.env.FFMPEG_DIR || firstExisting([
      path.join(resourceRoot, 'ffmpeg', 'bin'),
      path.join(root, 'ffmpeg', 'bin'),
    ], path.join(root, 'ffmpeg', 'bin')),
    PIPER_DIR: process.env.PIPER_DIR || firstExisting([
      path.join(resourceBase, 'piper'),
      path.join(externalResource, 'piper'),
    ], path.join(resourceBase, 'piper')),
  };

  if (mode === 'gpu') {
    env.F5_RESOURCE_DIR = process.env.F5_RESOURCE_DIR || firstExisting([
      path.join(resourceBase, 'f5'),
      path.join(externalResource, 'f5'),
    ], path.join(resourceBase, 'f5'));
  }

  if (app.isPackaged || process.env.CAPCAP_DATA_DIR) {
    env.CAPCAP_DATA_DIR = process.env.CAPCAP_DATA_DIR || dataRoot;
  }

  return env;
}

function resolvePython(mode, root) {
  const packagedPython = bundledPython(mode, root);
  if (packagedPython) {
    return { command: packagedPython, args: [] };
  }

  const installedPython = path.join(runtimeDir(mode), 'python.exe');
  if (fs.existsSync(installedPython)) {
    return { command: installedPython, args: [] };
  }

  if (process.env.CAPCAP_PYTHON) {
    return { command: process.env.CAPCAP_PYTHON, args: [] };
  }

  // A system Python is useful during development and after setup_portable.bat
  // has not yet been run. The backend gives a clear import error if packages
  // are missing.
  return { command: process.platform === 'win32' ? 'python.exe' : 'python3', args: [] };
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

function waitForBackend(url, child, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const startedAt = Date.now();
    let settled = false;
    const timer = setInterval(() => {
      if (settled) return;
      if (Date.now() - startedAt > timeoutMs) {
        settled = true;
        clearInterval(timer);
        reject(new Error(`Backend did not start within ${timeoutMs / 1000}s.`));
        return;
      }
      const request = http.get(`${url}/`, (response) => {
        response.resume();
        if (response.statusCode >= 200 && response.statusCode < 500 && !settled) {
          settled = true;
          clearInterval(timer);
          resolve();
        }
      });
      request.on('error', () => {});
      request.setTimeout(1500, () => request.destroy());
    }, 250);

    child.once('exit', (code, signal) => {
      if (settled) return;
      settled = true;
      clearInterval(timer);
      reject(new Error(`Backend exited before startup (code=${code}, signal=${signal || 'none'}).`));
    });
  });
}

function logBackend(mode, stream, message) {
  const logDir = path.join(app.getPath('userData'), 'logs');
  fs.mkdirSync(logDir, { recursive: true });
  const logPath = path.join(logDir, `${mode}.log`);
  fs.appendFileSync(logPath, `[${new Date().toISOString()}] ${message}`);
  stream.on('data', (chunk) => fs.appendFileSync(logPath, chunk));
}

async function startBackend(mode) {
  const root = appRoot();
  const backendDir = path.join(root, mode === 'cpu' ? 'backend_cpu' : 'backend');
  const backendMain = path.join(backendDir, 'main.py');
  if (!fs.existsSync(backendMain)) {
    throw new Error(`Không tìm thấy backend ${mode}: ${backendMain}`);
  }

  const port = await getFreePort();
  const python = resolvePython(mode, root);
  const env = configureEnvironment(mode);
  const pythonArgs = [...python.args, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(port)];
  env.PYTHONPATH = [backendDir, env.PYTHONPATH].filter(Boolean).join(path.delimiter);

  backendProcess = spawn(python.command, pythonArgs, {
    cwd: backendDir,
    env,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  logBackend(mode, backendProcess.stdout, `Starting ${python.command} ${pythonArgs.join(' ')}\n`);
  logBackend(mode, backendProcess.stderr, '');
  backendProcess.on('error', (error) => {
    const logDir = path.join(app.getPath('userData'), 'logs');
    fs.mkdirSync(logDir, { recursive: true });
    fs.appendFileSync(path.join(logDir, `${mode}.log`), `${error.stack || error}\n`);
  });

  backendUrl = `http://127.0.0.1:${port}`;
  await waitForBackend(backendUrl, backendProcess);
  return backendUrl;
}

function stopBackend() {
  if (!backendProcess || backendProcess.killed) return;
  const pid = backendProcess.pid;
  if (process.platform === 'win32') {
    spawn('taskkill', ['/pid', String(pid), '/t', '/f'], { windowsHide: true });
  } else {
    backendProcess.kill('SIGTERM');
  }
  backendProcess = null;
}

async function createWindow() {
  const mode = getMode();
  let setup = null;
  try {
    const root = appRoot();
    if (app.isPackaged && !bundledPython(mode, root) && !process.env.CAPCAP_PYTHON) {
      setup = createSetupWindow(mode);
      await setup.ready;
      await ensureRuntime(mode, setup.setupWindow);
    }
    const url = await startBackend(mode);
    if (setup?.setupWindow && !setup.setupWindow.isDestroyed()) setup.setupWindow.close();
    mainWindow = new BrowserWindow({
      width: 1440,
      height: 950,
      minWidth: 1000,
      minHeight: 700,
      icon: getAppIcon(),
      title: `CapCap TTS · ${mode.toUpperCase()}`,
      webPreferences: {
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
    });
    mainWindow.on('closed', () => { mainWindow = null; });
    await mainWindow.loadURL(url);
  } catch (error) {
    if (setup?.setupWindow && !setup.setupWindow.isDestroyed()) setup.setupWindow.close();
    stopBackend();
    dialog.showErrorBox('CapCap TTS không thể khởi động', `${error.message}\n\nKiểm tra Python/dependency và xem log trong thư mục dữ liệu ứng dụng.`);
    app.quit();
  }
}

app.whenReady().then(createWindow);
app.on('before-quit', stopBackend);
app.on('window-all-closed', () => app.quit());
