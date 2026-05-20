require('dotenv').config({ path: '../../.env' });

const axios = require('axios');

const SHOP = process.env.SHOPIFY_STORE;
const TOKEN = process.env.SHOPIFY_ACCESS_TOKEN;
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;

async function generateProductData() {

    const prompt = `
Create a Shopify product for a Warhammer 40k 3D printed terrain piece.

Return:
- title
- price
- SEO optimized description
- tags
`;

    const response = await axios.post(
        'https://api.anthropic.com/v1/messages',
        {
            model: 'claude-sonnet-4-20250514',
            max_tokens: 500,
            messages: [
                {
                    role: 'user',
                    content: prompt
                }
            ]
        },
        {
            headers: {
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }
        }
    );

    return response.data.content[0].text;
}

async function createShopifyProduct(aiText) {

    const titleMatch = aiText.match(/title:(.*)/i);
    const priceMatch = aiText.match(/price:(.*)/i);

    const title = titleMatch ? titleMatch[1].trim() : 'AI Product';
    const price = priceMatch ? priceMatch[1].trim() : '19.99';

    const response = await axios.post(
        `https://${SHOP}/admin/api/2025-04/products.json`,
        {
            product: {
                title,
                body_html: `<p>${aiText}</p>`,
                vendor: 'OpenJarvisNexus',
                product_type: '3D Print',
                variants: [
                    {
                        price
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

    console.log('AI PRODUCT CREATED');
    console.log(response.data.product.title);
}

async function run() {

    try {

        const aiData = await generateProductData();

        console.log(aiData);

        await createShopifyProduct(aiData);

    } catch (err) {

        console.log(err.response?.data || err.message);

    }

}

run();