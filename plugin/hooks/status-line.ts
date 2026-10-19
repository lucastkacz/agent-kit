// The batch's progress under the prompt (#108), from `agent-batch status --line`.
// A plugin can't set Claude Code's `statusLine`, and that setting's command wouldn't find
// `agent-batch` on its PATH: a mod finds it under the plugin's own folder.
import type { Register } from 'claude-code'

// Often enough to follow a lane from step to step; each time starts the runner's Python.
const PERIOD_MS = 5000

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    let isShowing = false
    const show = async () => {
      // A slow computer could take longer than a period: one run at a time.
      if (isShowing) return
      isShowing = true
      try {
        const ran = await $.process.run([`${$.plugin.root}/bin/agent-batch`, 'status', '--line'], {
          stdin: JSON.stringify({ cwd: await $.session.cwd() }),
        })
        const line = ran.exitCode === 0 ? ran.stdout.split('\n')[0].trim() : ''
        $.ui.status(line || undefined)
      } catch {
        $.ui.status(undefined)
      } finally {
        isShowing = false
      }
    }
    $.clock.after(1, show)
    $.clock.every(PERIOD_MS, show)
    return started
  })
}
