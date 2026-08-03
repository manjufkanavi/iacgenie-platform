import { useState, useEffect } from 'react';

export function useDeploymentLogs(deploymentId: string) {
  const [logs, setLogs] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!deploymentId) return;
    
    setLogs('');
    setIsConnected(false);
    
    // Determine WS protocol based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/deployments/ws/${deploymentId}/logs`;
    
    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;
    
    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          setIsConnected(true);
        };
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.message) {
              setLogs(prev => prev + (prev ? '\n' : '') + data.message);
            } else {
              setLogs(prev => prev + (prev ? '\n' : '') + JSON.stringify(data));
            }
          } catch (e) {
            setLogs(prev => prev + (prev ? '\n' : '') + event.data);
          }
        };
        
        ws.onclose = () => {
          setIsConnected(false);
          // Try to reconnect after 5s if we were not explicitly unmounted
          reconnectTimeout = setTimeout(connect, 5000);
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket Error: ', error);
          ws.close();
        };
        
      } catch (err) {
        console.error('WebSocket connection failed', err);
        reconnectTimeout = setTimeout(connect, 5000);
      }
    };
    
    connect();
    
    return () => {
      clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null; // Prevent reconnect
        ws.close();
      }
    };
  }, [deploymentId]);

  return { logs, isConnected };
}
