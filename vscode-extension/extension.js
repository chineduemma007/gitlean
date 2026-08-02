const vscode = require('vscode');
const { spawn } = require('child_process');
const path = require('path');
const axios = require('axios');

let proxyProcess = null;

/**
 * Activated when VS Code finishes loading.
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('GitLean Extension is now active!');

    // 1. Register Command: Start GitLean Proxy
    let startCommand = vscode.commands.registerCommand('gitlean.startProxy', () => {
        startLocalProxy();
    });
    context.subscriptions.push(startCommand);

    // 2. Register Command: Stop GitLean Proxy
    let stopCommand = vscode.commands.registerCommand('gitlean.stopProxy', () => {
        stopLocalProxy();
    });
    context.subscriptions.push(stopCommand);

    // 3. Register Command: Show Split-Screen Diff Visualizer
    let visualizerCommand = vscode.commands.registerCommand('gitlean.showDiffVisualizer', () => {
        openVisualizerPanel(context);
    });
    context.subscriptions.push(visualizerCommand);

    // Auto-start proxy on activation
    startLocalProxy();
}

/**
 * Launches the local Python GitLean proxy server in the background
 * and overrides terminal environment variables for new terminals.
 */
function startLocalProxy() {
    if (proxyProcess) {
        vscode.window.showInformationMessage('GitLean Proxy is already running.');
        return;
    }

    const config = vscode.workspace.getConfiguration('gitlean');
    const port = config.get('proxyPort') || 8000;
    const apiKey = config.get('paritokApiKey');

    // Locate Python runner path inside extension folder
    const scriptPath = path.join(__dirname, '..', 'run_backend.py');
    
    // Spawn python proxy process
    proxyProcess = spawn('python', [scriptPath, port.toString()], {
        env: {
            ...process.env,
            'PARITOK_API_KEY': apiKey,
            'PYTHONUTF8': '1'
        }
    });

    proxyProcess.stdout.on('data', (data) => {
        console.log(`[GitLean Backend]: ${data}`);
    });

    proxyProcess.stderr.on('data', (data) => {
        console.error(`[GitLean Backend Error]: ${data}`);
    });

    proxyProcess.on('close', (code) => {
        console.log(`GitLean proxy process exited with code ${code}`);
        proxyProcess = null;
    });

    // Automatically inject the proxy environment variable into VS Code terminal configurations
    const baseUri = `http://127.0.0.1:${port}/v1`;
    vscode.workspace.getConfiguration().update('terminal.integrated.env.windows', {
        'ANTHROPIC_BASE_URL': baseUri
    }, vscode.ConfigurationTarget.Global);
    
    vscode.workspace.getConfiguration().update('terminal.integrated.env.osx', {
        'ANTHROPIC_BASE_URL': baseUri
    }, vscode.ConfigurationTarget.Global);

    vscode.workspace.getConfiguration().update('terminal.integrated.env.linux', {
        'ANTHROPIC_BASE_URL': baseUri
    }, vscode.ConfigurationTarget.Global);

    vscode.window.showInformationMessage(`GitLean Context-Proxy started on port ${port}. New terminals will auto-route to GitLean!`);
}

/**
 * Kills the local Python proxy process.
 */
function stopLocalProxy() {
    if (!proxyProcess) {
        vscode.window.showInformationMessage('GitLean Proxy is not running.');
        return;
    }

    proxyProcess.kill();
    proxyProcess = null;

    // Reset environment variables
    vscode.workspace.getConfiguration().update('terminal.integrated.env.windows', {}, vscode.ConfigurationTarget.Global);
    vscode.workspace.getConfiguration().update('terminal.integrated.env.osx', {}, vscode.ConfigurationTarget.Global);
    vscode.workspace.getConfiguration().update('terminal.integrated.env.linux', {}, vscode.ConfigurationTarget.Global);

    vscode.window.showInformationMessage('GitLean Proxy stopped.');
}

/**
 * Opens a split-screen visualizer webview directly inside VS Code
 * instead of requiring an external browser tab.
 */
function openVisualizerPanel(context) {
    const panel = vscode.window.createWebviewPanel(
        'gitleanVisualizer',
        '🔍 GitLean Context Visualizer',
        vscode.ViewColumn.Two, // Open side-by-side
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );

    // Point webview to GitLean Vite dev server
    panel.webview.html = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>GitLean Context Visualizer</title>
            <style>
                html, body, iframe {
                    margin: 0; padding: 0; width: 100%; height: 100%; border: none; overflow: hidden;
                    background: #020617;
                }
            </style>
        </head>
        <body>
            <iframe src="http://localhost:5173/"></iframe>
        </body>
        </html>
    `;
}

function deactivate() {
    stopLocalProxy();
}

module.exports = {
    activate,
    deactivate
}
