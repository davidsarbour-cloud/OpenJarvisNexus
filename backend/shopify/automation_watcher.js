require('dotenv').config({ path: '../../.env' });

const fs = require('fs');
const path = require('path');
const axios = require('axios');

const SHOP = process.env.SHOPIFY_STORE;
const TOKEN = process.env.SHOPIFY_ACCESS_TOKEN;

const WATCH_FOLDER = './automation/incoming';

console.log('🔥 WATCHING FOR NEW STL FILES...');

function cleanTitle(filename) {

    return filename
        .replace('.stl', '')
        .replace('.png', '')
        .replace('.jpg', '')
        .replaceAll('_', ' ')
        .replaceAll('-', ' ');
}

function generateTags(title) {

    const autoTags = title
        .split(' ')
        .filter(Boolean)
        .join(', ');

    return `${autoTags}, 3d print, tabletop, miniature, stl`;
}

function generateDescription(title, price) {

    return `
    <h2>${title}</h2>

    <p>
    Premium 3D printed collectible model.
    </p>

    <ul>
        <li>High detail print quality</li>
        <li>Perfect for painting</li>
        <li>Ideal for tabletop gaming</li>
        <li>Carefully prepared by OpenJarvis Nexus</li>
    </ul>

    <p>
    Price: $${price}
    </p>
    `;
}

function calculatePrice(title, filePath) {

    let basePrice = 19.99;

    if (title.includes('large'))
        basePrice = 39.99;

    if (title.includes('small'))
        basePrice = 9.99;

    if (title.includes('terrain'))
        basePrice += 10;

    try {

        const stats = fs.statSync(filePath);

        const mb = stats.size / 1024 / 1024;

        basePrice += mb * 2;

    } catch {}

    return basePrice.toFixed(2);
}

async function uploadImage(productId, imagePath) {

    try {

        const imageBase64 = fs.readFileSync(
            imagePath,
            { encoding: 'base64' }
        );

        await axios.post(
            `https://${SHOP}/admin/api/2025-04/products/${productId}/images.json`,
            {
                image: {
                    attachment: imageBase64
                }
            },
            {
                headers: {
                    'X-Shopify-Access-Token': TOKEN,
                    'Content-Type': 'application/json'
                }
            }
        );

        console.log('🖼 IMAGE UPLOADED');

    } catch (err) {

        console.log('❌ IMAGE ERROR');

        console.log(
            err.response?.data || err.message
        );
    }
}

async function createProduct(filename) {

    const title = cleanTitle(filename);

    const filePath =
        `${WATCH_FOLDER}/${filename}`;

    const imagePath =
        `${WATCH_FOLDER}/${path.parse(filename).name}.jpg`;

    const tags = generateTags(title);

    const price = calculatePrice(
        title,
        filePath
    );

    const description =
        generateDescription(title, price);

    try {

        const response = await axios.post(
            `https://${SHOP}/admin/api/2025-04/products.json`,
            {
                product: {
                    title,
                    body_html: description,
                    vendor: 'OpenJarvisNexus',
                    product_type: '3D Print',
                    tags,
                    status: 'active',
                    variants: [
                        {
                            price,
                            inventory_quantity: 10
                        }
                    ]
                }
            },
            {
                headers: {
                    'X-Shopify-Access-Token': TOKEN,
                    'Content-Type': 'application/json'
                }
            }
        );

        const product =
            response.data.product;

        console.log(
            `✅ SHOPIFY PRODUCT CREATED: ${title}`
        );

        console.log(
            `💲 PRICE: $${price}`
        );

        console.log(
            `🏷 TAGS: ${tags}`
        );

        if (fs.existsSync(imagePath)) {

            await uploadImage(
                product.id,
                imagePath
            );

        } else {

            console.log(
                '⚠ No matching JPG found'
            );

        }

    } catch (err) {

        console.log(
            err.response?.data || err.message
        );
    }
}

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

        await createProduct(filename);
    }
);