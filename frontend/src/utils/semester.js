const CHINESE_TERMS = ['第一学期', '第二学期']

export function currentAcademicYearStart(date = new Date()) {
  const month = date.getMonth() + 1
  const year = date.getFullYear()
  return month >= 8 ? year : year - 1
}

export function currentSemesterTerm(date = new Date()) {
  const month = date.getMonth() + 1
  return month >= 8 || month <= 1 ? '第一学期' : '第二学期'
}

export function formatSemester(startYear, term) {
  const year = Number(startYear)
  if (!Number.isInteger(year) || year < 2000 || year > 2100) return ''
  const normalizedTerm = term === '第二学期' || term === '2' || term === 2 ? '第二学期' : '第一学期'
  return `${year}-${year + 1}${normalizedTerm}`
}

export function normalizeSemester(value) {
  const text = String(value || '').replace(/\s+/g, '').replace(/[—–]/g, '-')
  if (!text) return ''
  const match = text.match(/^(\d{4})-(\d{4})(?:第)?([一二12])学期$/)
  if (!match) return text
  const start = Number(match[1])
  const end = Number(match[2])
  if (end !== start + 1) return text
  const term = match[3] === '1' || match[3] === '一' ? '第一学期' : '第二学期'
  return `${start}-${end}${term}`
}

export function isStandardSemester(value) {
  const normalized = normalizeSemester(value)
  const match = normalized.match(/^(\d{4})-(\d{4})第[一二]学期$/)
  return Boolean(match && Number(match[2]) === Number(match[1]) + 1)
}

export function parseSemester(value) {
  const normalized = normalizeSemester(value)
  const match = normalized.match(/^(\d{4})-(\d{4})(第一学期|第二学期)$/)
  if (!match || Number(match[2]) !== Number(match[1]) + 1) {
    const startYear = currentAcademicYearStart()
    const term = currentSemesterTerm()
    return { startYear, term, value: formatSemester(startYear, term) }
  }
  return {
    startYear: Number(match[1]),
    term: match[3],
    value: normalized
  }
}

export function buildSemesterOptions(rangeBefore = 3, rangeAfter = 1) {
  const current = currentAcademicYearStart()
  const options = []
  for (let year = current + rangeAfter; year >= current - rangeBefore; year -= 1) {
    for (const term of CHINESE_TERMS) {
      options.push(`${year}-${year + 1}${term}`)
    }
  }
  return options
}

export function mergeSemesterOptions(existingValues = [], generatedOptions = buildSemesterOptions()) {
  const normalizedExisting = existingValues
    .map((value) => normalizeSemester(value))
    .filter(Boolean)
  return [...new Set([...generatedOptions, ...normalizedExisting])]
}
