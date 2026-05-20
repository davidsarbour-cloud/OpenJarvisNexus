const sharp = require('sharp');

sharp('./images/terrain.webp')
  .jpeg({ quality: 95 })
  .toFile('./images/terrain.jpg')
  .then(() => console.log('Converted to JPG'))
  .catch(err => console.error(err));