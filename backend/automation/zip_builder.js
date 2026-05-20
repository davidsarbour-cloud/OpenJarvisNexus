const fs = require('fs');
const archiver = require('archiver');

async function createZipPack(
    title,
    files
) {

    return new Promise((resolve, reject) => {

        const zipPath =
            `./automation/processed/${title}.zip`;

        const output =
            fs.createWriteStream(zipPath);

        const archive =
            archiver('zip', {
                zlib: { level: 9 }
            });

        output.on('close', () => {

            console.log(
                `ZIP CREATED: ${zipPath}`
            );

            resolve(zipPath);
        });

        archive.on('error', reject);

        archive.pipe(output);

        files.forEach(file => {

            if (fs.existsSync(file)) {

                archive.file(
                    file,
                    {
                        name: file.split('/').pop()
                    }
                );
            }

        });

        archive.finalize();

    });
}

module.exports = {
    createZipPack
};