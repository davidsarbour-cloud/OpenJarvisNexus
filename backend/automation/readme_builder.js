const fs = require('fs');
const path = require('path');

async function createReadme(
    metadata
) {

    const baseName =
        path.parse(
            metadata.stlPath
        ).name;

    const readmePath =
        `./automation/incoming/${baseName}_README.txt`;

    const content = `
========================================
OPENJARVIS NEXUS
========================================

PRODUCT
----------------------------------------

${metadata.title}

========================================
DESCRIPTION
========================================

${metadata.description}

========================================
PRINT SETTINGS
========================================

Recommended Layer Height:
0.2mm

Supports:
Recommended if necessary

Infill:
15% - 20%

Material:
PLA / Resin compatible

========================================
LICENSE
========================================

PERSONAL USE ONLY

You may:
- Print models for personal use
- Paint and display models

You may NOT:
- Resell STL files
- Redistribute files
- Upload files elsewhere
- Share files publicly

Commercial rights are NOT included.

========================================
THANK YOU
========================================

Thank you for supporting OpenJarvis Nexus.

Enjoy your print!
`;

    fs.writeFileSync(
        readmePath,
        content
    );

    console.log(
        `📄 README CREATED: ${readmePath}`
    );

    return readmePath;
}

module.exports = {
    createReadme
};