#!/usr/bin/env node

const { spawn } = require('child_process');
const net = require('net');

/**
 * Check if a port is available
 */
function checkPort(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    
    server.listen(port, () => {
      server.once('close', () => {
        resolve(true);
      });
      server.close();
    });
    
    server.on('error', () => {
      resolve(false);
    });
  });
}

/**
 * Find an available port starting from the preferred port
 */
async function findAvailablePort(preferredPort, fallbackPort) {
  const isPreferredAvailable = await checkPort(preferredPort);
  
  if (isPreferredAvailable) {
    return preferredPort;
  }
  
  console.log(`Port ${preferredPort} is already in use, trying port ${fallbackPort}...`);
  
  const isFallbackAvailable = await checkPort(fallbackPort);
  
  if (isFallbackAvailable) {
    return fallbackPort;
  }
  
  throw new Error(`Both port ${preferredPort} and ${fallbackPort} are in use. Please free up a port.`);
}

/**
 * Start Next.js dev server on the specified port
 */
async function startDevServer() {
  try {
    const port = await findAvailablePort(3001, 3000);
    console.log(`Starting Next.js dev server on port ${port}...`);
    
    const nextProcess = spawn('next', ['dev', '-p', port.toString()], {
      stdio: 'inherit',
      shell: true
    });
    
    nextProcess.on('error', (error) => {
      console.error('Failed to start Next.js:', error);
      process.exit(1);
    });
    
    nextProcess.on('exit', (code) => {
      process.exit(code || 0);
    });
    
    // Handle termination signals
    process.on('SIGTERM', () => {
      nextProcess.kill('SIGTERM');
    });
    
    process.on('SIGINT', () => {
      nextProcess.kill('SIGINT');
    });
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

startDevServer();

