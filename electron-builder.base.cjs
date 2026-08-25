const fs = require('fs');

module.exports = function makeConfig(mode) {
  if (!fs.existsSync(require('path').join(__dirname, 'python-embed.zip'))) {
    throw new Error('python-embed.zip is missing. Run npm run prepare:runtime before building.');
  }
  const backendDir = mode === 'cpu' ? 'backend_cpu' : 'backend';
  const resources = [
    { from: 'python-embed.zip', to: 'python-embed.zip' },
    { from: 'frontend', to: 'frontend' },
    {
      from: backendDir,
      to: backendDir,
      filter: ['**/*', '!outputs/**', '!**/__pycache__/**', '!**/*.pyc', '!custom_dict/_combined/**'],
    },
    { from: 'ffmpeg', to: 'ffmpeg' },
  ];

  return {
    appId: `com.capcap.tts.${mode}`,
    productName: `CapCap TTS ${mode.toUpperCase()}`,
    artifactName: 'CapCap-TTS-' + mode.toUpperCase() + '-${version}-${arch}.${ext}',
    directories: { output: `dist-electron/${mode}` },
    files: ['electron/**/*', 'package.json'],
    extraResources: resources,
    asar: true,
    win: { target: [{ target: 'nsis', arch: ['x64'] }] },
    nsis: { oneClick: false, allowToChangeInstallationDirectory: true },
    extraMetadata: { main: `electron/main-${mode}.cjs` },
  };
};
