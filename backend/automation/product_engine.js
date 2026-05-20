const fs = require('fs');
const path = require('path');

const {
    uploadShopify
} = require('../shopify/shopify_integration');

const {
    createZipPack
} = require('./zip_builder');

const {
    createReadme
} = require('./readme_builder');

const PROCESSED_FOLDER =
    './automation/processed';

const FAILED_FOLDER =
    './automation/failed';

async function moveFile(
    source,
    destination
) {

    if (!fs.existsSync(source))
        return;

    fs.renameSync(
        source,
        destination
    );
}

async function processProduct(
    metadata
) {

    console.log(
        '\n🧠 PROCESSING PRODUCT'
    );

    console.log(metadata);

    try {

        const baseName =
            path.parse(
                metadata.stlPath
            ).name;

        // =====================================
        // AUTO README
        // =====================================

        const readmePath =
            await createReadme(
                metadata
            );

        // =====================================
        // FILE COLLECTION
        // =====================================

        const zipFiles = [];

        // STL
        if (
            fs.existsSync(
                metadata.stlPath
            )
        ) {

            zipFiles.push(
                metadata.stlPath
            );
        }

        // JPG PREVIEW
        if (
            fs.existsSync(
                metadata.imagePath
            )
        ) {

            zipFiles.push(
                metadata.imagePath
            );
        }

        // README
        if (
            fs.existsSync(
                readmePath
            )
        ) {

            zipFiles.push(
                readmePath
            );
        }

        // 3MF SUPPORT
        const threeMfPath =
            `./automation/incoming/${baseName}.3mf`;

        if (
            fs.existsSync(
                threeMfPath
            )
        ) {

            zipFiles.push(
                threeMfPath
            );
        }

        // =====================================
        // ZIP CREATION
        // =====================================

        const zipPath =
            await createZipPack(
                baseName,
                zipFiles
            );

        metadata.zipPath =
            zipPath;

        console.log(
            `📦 ZIP CREATED: ${zipPath}`
        );

        // =====================================
        // SHOPIFY MODULE
        // =====================================

        await uploadShopify(
            metadata
        );

        // =====================================
        // FUTURE MARKETPLACE MODULES
        // =====================================

        /*
        await uploadEtsy(metadata)

        await uploadGumroad(metadata)

        await uploadThingiverse(metadata)

        await uploadPrintables(metadata)
        */

        // =====================================
        // MOVE FILES TO PROCESSED
        // =====================================

        const processedStl =
            `${PROCESSED_FOLDER}/${path.basename(metadata.stlPath)}`;

        await moveFile(
            metadata.stlPath,
            processedStl
        );

        // JPG
        if (
            fs.existsSync(
                metadata.imagePath
            )
        ) {

            const processedImage =
                `${PROCESSED_FOLDER}/${path.basename(metadata.imagePath)}`;

            await moveFile(
                metadata.imagePath,
                processedImage
            );
        }

        // README
        if (
            fs.existsSync(
                readmePath
            )
        ) {

            const processedReadme =
                `${PROCESSED_FOLDER}/${path.basename(readmePath)}`;

            await moveFile(
                readmePath,
                processedReadme
            );
        }

        // ZIP
        if (
            fs.existsSync(
                zipPath
            )
        ) {

            const processedZip =
                `${PROCESSED_FOLDER}/${path.basename(zipPath)}`;

            await moveFile(
                zipPath,
                processedZip
            );
        }

        // 3MF
        if (
            fs.existsSync(
                threeMfPath
            )
        ) {

            const processed3mf =
                `${PROCESSED_FOLDER}/${path.basename(threeMfPath)}`;

            await moveFile(
                threeMfPath,
                processed3mf
            );
        }

        console.log(
            `✅ PRODUCT COMPLETED`
        );

    } catch (err) {

        console.log(
            '\n❌ PRODUCT FAILED'
        );

        console.log(
            err.message
        );

        try {

            const failedStl =
                `${FAILED_FOLDER}/${path.basename(metadata.stlPath)}`;

            await moveFile
                metadata.stlPath,
                failedStl
            ;

        } catch {}

    }

}

module.exports = {
    processProduct
};