require('dotenv').config({ path: '../../.env' });

const fs = require('fs');
const path = require('path');

const { buildMetadata } =
    require('./metadata_builder');

const { processProduct } =
    require('./product_engine');

const WATCH_FOLDER =
    './automation/incoming';

console.log(
    '🔥 UNIVERSAL PIPELINE WATCHER ACTIVE'
);

fs.watch(
    WATCH_FOLDER,
    async (eventType, filename) => {

        if (!filename)
            return;

        if (
            !filename.endsWith('.stl')
        )
            return;

        console.log(
            `📦 NEW STL DETECTED: ${filename}`
        );

        try {

            const metadata =
                await buildMetadata(filename);

            await processProduct(metadata);

        } catch (err) {

            console.log(err.message);

        }

    }
);