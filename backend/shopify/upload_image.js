require('dotenv').config({ path: '../../.env' });

const axios = require('axios');
const fs = require('fs');

const SHOP = process.env.SHOPIFY_STORE;
const TOKEN = process.env.SHOPIFY_ACCESS_TOKEN;

async function uploadImage() {
  try {
    const imageBase64 = fs.readFileSync('./images/terrain.jpg', {
      encoding: 'base64',
    });

    const response = await axios.put(
      `https://${SHOP}/admin/api/2025-04/products/9144071389336.json`,
      {
        product: {
          id: 9144071389336,
          images: [
            {
              attachment: imageBase64,
            },
          ],
        },
      },
      {
        headers: {
          'X-Shopify-Access-Token': TOKEN,
          'Content-Type': 'application/json',
        },
      }
    );

    console.log('IMAGE UPLOADED');
    console.log(response.data);
  } catch (err) {
    console.log('ERROR');
    console.log(err.response?.data || err.message);
  }
}

uploadImage();