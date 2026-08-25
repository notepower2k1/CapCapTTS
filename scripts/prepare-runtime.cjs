const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const projectRoot = path.resolve(__dirname, '..');
const source = path.join(projectRoot, 'python-portable-cpu');
const output = path.join(projectRoot, 'python-embed.zip');

if (!fs.existsSync(path.join(source, 'python.exe'))) {
  throw new Error('python-portable-cpu is missing. Run setup_portable.bat cpu first.');
}

const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'capcap-python-'));
try {
  for (const entry of fs.readdirSync(source)) {
    if (entry === 'Lib' || entry === 'Scripts') continue;
    fs.cpSync(path.join(source, entry), path.join(temp, entry), { recursive: true });
  }
  const quote = (value) => `'${value.replace(/'/g, "''")}'`;
  const command = `Compress-Archive -Path ${quote(path.join(temp, '*'))} -DestinationPath ${quote(output)} -Force`;
  const result = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', command], { stdio: 'inherit' });
  if (result.status !== 0) throw new Error(`Could not create ${output}`);
  console.log(`Created ${output} (${Math.round(fs.statSync(output).size / 1024 / 1024)} MB)`);
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
