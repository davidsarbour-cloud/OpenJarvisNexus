require('dotenv').config({ path: '../../.env' });

const axios = require('axios');

const SHOP = process.env.SHOPIFY_STORE;
const TOKEN = process.env.SHOPIFY_ACCESS_TOKEN;

async function createProduct() {
    try {

        const productData = {
            product: {
                title: "AI Generated Warhammer Terrain",
                body_html: "<strong>3D printed sci-fi terrain piece.</strong>",
                vendor: "OpenJarvisNexus",
                product_type: "3D Print",
                variants: [
                    {
                        price: "24.99",
                        inventory_quantity: 10
                    }
                ]
            }
        };

        const response = await axios.post(
            `https://${SHOP}/admin/api/2025-01/products.json`,
            productData,
            {
                headers: {
                    'X-Shopify-Access-Token': TOKEN,
                    'Content-Type': 'application/json'
                }
            }
        );

        console.log('PRODUCT CREATED');
        console.log(response.data);

    } catch (error) {

        console.log('ERROR');
        
        if (error.response) {
            console.log(error.response.data);
        } else {
            console.log(error.message);
        }
    }
}

createProduct();