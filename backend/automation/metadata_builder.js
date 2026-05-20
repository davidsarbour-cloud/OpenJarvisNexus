const path = require('path');
const fs = require('fs');

async function buildMetadata(filename) {

    const cleanTitle =
        path.parse(filename).name
            .replaceAll('_', ' ')
            .replaceAll('-', ' ');

    const imagePath =
        `./automation/incoming/${path.parse(filename).name}.jpg`;

    const stlPath =
        `./automation/incoming/${filename}`;

    const tags =
        cleanTitle.split(' ').join(', ');

    let price = 19.99;

    try {

        const stats =
            fs.statSync(stlPath);

        const mb =
            stats.size / 1024 / 1024;

        price += mb * 2;

    } catch {}

    return {

        title: cleanTitle,

        description:
            `Premium 3D printed ${cleanTitle}.`,

        tags:
            `${tags}, 3d print, tabletop`,

        price:
            price.toFixed(2),

        imagePath,

        stlPath
    };
}

module.exports = {
    buildMetadata
};