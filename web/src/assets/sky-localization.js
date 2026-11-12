import catalog from './sky-zh-cn.json'

function designationKey (name) {
  return name.normalize('NFKC').trim().toLowerCase().replace(/^name\s+/, '').replace(/\s+/g, '')
}

const objectNames = new Map()
for (const { zh, names } of catalog.objects) {
  for (const name of names) objectNames.set(designationKey(name), zh)
}

const constellationNames = new Map(
  Object.values(catalog.constellations).map(({ name, zh }) => [designationKey(name), zh])
)
const constellationCodes = new Map(
  Object.entries(catalog.constellations).map(([key, { zh }]) => [key.toLowerCase(), zh])
)

const sourceTypes = {
  '*': '恒星', '**': '双星', 'V*': '变星', dso: '深空天体', G: '星系',
  GCl: '星系团', OpC: '疏散星团', GlC: '球状星团', Cl: '星团',
  Neb: '星云', HII: '电离氢区', PN: '行星状星云', SNR: '超新星遗迹',
  SSO: '太阳系天体', Pla: '行星', Moo: '卫星', MPl: '小行星', Com: '彗星', Con: '星座'
}

export function localizedSkySourceType (type, locale) {
  return locale === 'cn' && Object.prototype.hasOwnProperty.call(sourceTypes, type) ? sourceTypes[type] : undefined
}

export function translateSkyLabel (domain, label) {
  if (domain === 'gui' && Object.prototype.hasOwnProperty.call(catalog.directions, label)) {
    return catalog.directions[label]
  }
  if (domain === 'skyculture') return constellationNames.get(designationKey(label)) || label
  if (domain === 'sky') return objectNames.get(designationKey(label)) || label
  return label
}

export function localizedSkySourceName (source, locale) {
  if (locale !== 'cn' || !source || !source.names) return undefined
  for (const name of source.names) {
    const key = designationKey(name)
    const localized = objectNames.get(key) || constellationNames.get(key)
    if (localized) return localized
  }
  const abbreviation = source.model === 'constellation' && source.model_data?.iau_abbreviation
  return abbreviation && constellationCodes.get(abbreviation.toLowerCase())
}
