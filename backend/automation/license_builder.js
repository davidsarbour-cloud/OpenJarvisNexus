const fs = require('fs');
const path = require('path');

async function createLicense(
    metadata
) {

    const baseName =
        path.parse(
            metadata.stlPath
        ).name;

    const licensePath =
        `./automation/incoming/${baseName}_LICENSE.txt`;

    const content = `
========================================
OPENJARVIS NEXUS LICENSE
========================================

PERSONAL USE ONLY

You may:
- Print for personal use
- Paint and display models

You may NOT:
- Resell STL files
- Redistribute files
- Upload files elsewhere
- Share files publicly

Commercial rights are NOT included.

========================================
`;

    fs.writeFileSync(
        licensePath,
        content
    );

    console.log(
        `📜 LICENSE CREATED`
    );

    return licensePath;
}

module.exports = {
    createLicense
};