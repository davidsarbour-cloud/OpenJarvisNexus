require('dotenv').config({ path: '../../.env' });

const axios = require('axios');
const fs = require('fs');

const SHOP =
    process.env.SHOPIFY_STORE;

const TOKEN =
    process.env.SHOPIFY_ACCESS_TOKEN;

async function uploadImage(
    productId,
    imagePath
) {

    if (!fs.existsSync(imagePath)) {

        console.log(
            '⚠ NO IMAGE FOUND'
        );

        return;
    }

    const imageBase64 =
        fs.readFileSync(
            imagePath,
            {
                encoding: 'base64'
            }
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
                'X-Shopify-Access-Token':
                    TOKEN,

                'Content-Type':
                    'application/json'
            }
        }
    );

    console.log(
        '🖼 IMAGE UPLOADED'
    );
}

async function uploadShopify(
    metadata
) {

    const response =
        await axios.post(
            `https://${SHOP}/admin/api/2025-04/products.json`,
            {
                product: {

                    title:
                        metadata.title,

                    body_html:
                        metadata.description,

                    vendor:
                        'OpenJarvisNexus',

                    product_type:
                        '3D Print',

                    tags:
                        metadata.tags,

                    status:
                        'active',

                    variants: [
                        {
                            price:
                                metadata.price
                        }
                    ]
                }
            },
            {
                headers: {
                    'X-Shopify-Access-Token':
                        TOKEN,

                    'Content-Type':
                        'application/json'
                }
            }
        );

    const product =
        response.data.product;

    console.log(
        `✅ SHOPIFY PRODUCT CREATED: ${metadata.title}`
    );

    await uploadImage(
        product.id,
        metadata.imagePath
    );
}

module.exports = {
    uploadShopify
};