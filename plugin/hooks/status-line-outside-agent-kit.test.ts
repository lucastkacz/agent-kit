import { expect, mock, test } from 'claude-code/testing'

// Outside a project that enables agent-kit, `agent-batch status --line` prints nothing (#171).
test('when agent-batch status --line prints nothing, the mod shows no line', async ($, on) => {
  const clock = mock.clock(on)
  const shown: (string | undefined)[] = []
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: '/work/elsewhere' }))
  on('process.run', () => ({
    value: { exitCode: 0, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('ui.status', (_$, e) => {
    shown.push(e.text)
    return { value: undefined }
  })

  await $.session.start({ cwd: '/work/elsewhere', surface: 'terminal', isInteractive: true })
  await clock.advance(6000)

  expect(shown.length).toBeGreaterThan(0)
  expect(shown.every(text => text === undefined)).toBe(true)
})
