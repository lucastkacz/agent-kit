import { expect, mock, test } from 'claude-code/testing'

const LINE = 'L1 #75 review 2/2 · ship #79 review 1/1'

test('the status line shows what agent-batch status --line prints', async ($, on) => {
  const clock = mock.clock(on)
  const shown: (string | undefined)[] = []
  const ran: { argv: readonly string[]; stdin?: string }[] = []
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: '/work/project' }))
  on('process.run', (_$, e) => {
    ran.push({ argv: e.argv, stdin: e.init?.stdin })
    const stdout = `${LINE}\n`
    return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('ui.status', (_$, e) => {
    shown.push(e.text)
    return { value: undefined }
  })

  await $.session.start({ cwd: '/work/project', surface: 'terminal' })
  await clock.advance(6000)

  expect(shown.at(-1)).toBe(LINE)
  expect(ran[0].argv.slice(1)).toEqual(['status', '--line'])
  expect(ran[0].argv[0]).toMatch(/\/bin\/agent-batch$/)
  expect(JSON.parse(ran[0].stdin ?? '{}')).toEqual({ cwd: '/work/project' })
})

test('a run that fails clears the status line', async ($, on) => {
  const clock = mock.clock(on)
  const shown: (string | undefined)[] = []
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: '/work/project' }))
  on('process.run', () => ({
    value: { exitCode: 1, stdout: 'half a line', stderr: 'agent-batch: broke', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('ui.status', (_$, e) => {
    shown.push(e.text)
    return { value: undefined }
  })

  await $.session.start({ cwd: '/work/project', surface: 'terminal' })
  await clock.advance(6000)

  expect(shown.length).toBeGreaterThan(0)
  expect(shown.every(text => text === undefined)).toBe(true)
})
