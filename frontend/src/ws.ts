type Handler = (payload: any) => void

class WsClient {
  private socket: WebSocket | null = null
  private deviceName = ''
  private handlers = new Map<string, Set<Handler>>()
  private binaryHandlers = new Set<(data: ArrayBuffer) => void>()
  private reconnectTimer: number | null = null

  connect(deviceName: string): void {
    this.deviceName = deviceName
    this._open()
  }

  private _open(): void {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const socket = new WebSocket(`${protocol}://${location.host}/ws`)
    socket.binaryType = 'arraybuffer'
    this.socket = socket

    socket.onopen = () => {
      socket.send(JSON.stringify({ type: 'hello', payload: { deviceName: this.deviceName } }))
    }
    socket.onmessage = (event) => {
      if (typeof event.data !== 'string') {
        for (const handler of this.binaryHandlers) handler(event.data)
        return
      }
      const message = JSON.parse(event.data)
      const set = this.handlers.get(message.type)
      if (set) for (const handler of set) handler(message.payload)
    }
    socket.onclose = () => {
      this.reconnectTimer = window.setTimeout(() => this._open(), 1000)
    }
  }

  on(type: string, handler: Handler): void {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set())
    this.handlers.get(type)!.add(handler)
  }

  off(type: string, handler: Handler): void {
    this.handlers.get(type)?.delete(handler)
  }

  onBinary(handler: (data: ArrayBuffer) => void): void {
    this.binaryHandlers.add(handler)
  }

  offBinary(handler: (data: ArrayBuffer) => void): void {
    this.binaryHandlers.delete(handler)
  }

  send(type: string, payload: Record<string, unknown> = {}): void {
    this.socket?.send(JSON.stringify({ type, payload }))
  }

  sendBinary(data: ArrayBuffer): void {
    this.socket?.send(data)
  }

  disconnect(): void {
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer)
    this.socket?.close()
    this.socket = null
  }
}

export const ws = new WsClient()
