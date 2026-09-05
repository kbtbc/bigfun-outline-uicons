const fs = require('fs')

const SKIP_DIRS = new Set([
  'node_modules',
  'scripts',
  'docs',
  '.cursor',
  '.github',
])

module.exports.update = async function update() {
  const sorter = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })
  const checkFolders = async (folder) => {
    folder = folder.replace('//', '/')
    const files = await fs.promises.readdir(folder)
    let newJson = {}
    let hasSubFolders = false

    await Promise.all(files.map(async file => {
      if (file.startsWith('.') || SKIP_DIRS.has(file)) {
        return
      }
      if (!file.includes('.')) {
        hasSubFolders = true
        newJson[file] = await checkFolders(`${folder}/${file}`)
      }
    }))
    if (!hasSubFolders) {
      newJson = files.filter(file => file.includes('.png')).sort(sorter.compare)
    } else {
      const tempJson = newJson
      const sortedKeys = Object.keys(newJson).sort(sorter.compare)
      newJson = {}
      sortedKeys.forEach(key => (newJson[key] = tempJson[key]))
    }
    fs.writeFile(`./${folder === './' ? '' : `${folder}/`}index.json`, JSON.stringify(newJson, null, 2), 'utf8', () => {})
    return newJson
  }
  await checkFolders('./')
}
