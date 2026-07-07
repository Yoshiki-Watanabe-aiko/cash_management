import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled UI error', error, errorInfo)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-background p-6 text-center">
          <h1 className="text-lg font-semibold text-foreground">予期しないエラーが発生しました</h1>
          <p className="text-sm text-muted-foreground">ページを再読み込みしてください。問題が続く場合は開発者に連絡してください。</p>
        </div>
      )
    }
    return this.props.children
  }
}
