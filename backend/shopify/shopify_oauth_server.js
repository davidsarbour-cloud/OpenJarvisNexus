require("dotenv").config();

const express = require("express");
const crypto = require("crypto");
const axios = require("axios");

const app = express();

const PORT = 4001;

const SHOPIFY_API_KEY = process.env.SHOPIFY_API_KEY;
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET;
const SHOPIFY_REDIRECT_URI = process.env.SHOPIFY_REDIRECT_URI;
const SHOPIFY_SCOPES = process.env.SHOPIFY_SCOPES;

let stateStore = {};

app.get("/", (req, res) => {
    res.send("Shopify OAuth server running");
});

app.get("/auth/shopify", async (req, res) => {

    const shop = req.query.shop;

    if (!shop) {
        return res.status(400).send(
            "Missing ?shop=yourstore.myshopify.com"
        );
    }

    const state = crypto
        .randomBytes(16)
        .toString("hex");

    stateStore[state] = true;

    const installUrl =
        `https://${shop}/admin/oauth/authorize` +
        `?client_id=${SHOPIFY_API_KEY}` +
        `&scope=${SHOPIFY_SCOPES}` +
        `&redirect_uri=${encodeURIComponent(SHOPIFY_REDIRECT_URI)}` +
        `&state=${state}`;

    console.log("\n🔗 Redirecting to Shopify OAuth");
    console.log(installUrl);

    res.redirect(installUrl);
});

app.get("/auth/callback", async (req, res) => {

    const { shop, code, state } = req.query;

    if (!state || !stateStore[state]) {
        return res.status(400).send("Invalid state");
    }

    delete stateStore[state];

    try {

        const tokenResponse = await axios.post(
            `https://${shop}/admin/oauth/access_token`,
            {
                client_id: SHOPIFY_API_KEY,
                client_secret: SHOPIFY_API_SECRET,
                code
            }
        );

        const accessToken =
            tokenResponse.data.access_token;

        console.log("\n✅ SHOPIFY CONNECTED");
        console.log("Shop:", shop);
        console.log(
            "Access Token:",
            accessToken
        );

        res.send(`
            <h1>✅ Shopify Connected</h1>
            <p>You can close this window.</p>
        `);

    } catch (err) {

        console.error(
            err.response?.data || err.message
        );

        res.status(500).send("OAuth failed");
    }
});

app.listen(PORT, () => {
    console.log(
        `Shopify OAuth server running on port ${PORT}`
    );
});