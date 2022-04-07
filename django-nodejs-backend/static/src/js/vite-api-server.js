import express from 'express';
import bodyParser from 'body-parser';
import { 
    sleep,
    createWallet, 
    checkBalance, 
    sendTransaction, 
    receiveTransactions,

} from './vite-api-wallet.js';


const app = express()
const port = 3003
app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());


app.post('/create/', (req, res) => {
    try {
        // Create new Vite wallet
        const wallet = createWallet();

        // Create first address
        const firstAddress = wallet.deriveAddress(0);
        const { originalAddress, publicKey, privateKey, address, path } = firstAddress;

        // Prepare response object
        const obj = {
            'mnemonics': wallet.mnemonics,
            'address': address,
        }
        res.json(obj);
    } catch (e) {
        console.log('GET ERROR: \n', e);
    };
});


app.post('/balance/', async (req, res) => {
    // Get balance
     try {
        const { balance, unreceived } = await checkBalance(req.body.mnemonics)
        console.log(balance, unreceived)

        if (parseInt(unreceived.blockCount)) {
            console.log('New transactions, updating...');
            await receiveTransactions(req.body.mnemonics);
            balance.pendingTransactions = true
            res.json(balance);

        } else {
            // Return response object
            console.log('No new transactions, balance:');
            balance.pendingTransactions = false
            res.json(balance);
        };
    } catch (e) {
        console.log('GET ERROR: \n', e);
    };
});


app.post('/send_transaction/', async (req, res) => {
    const { mnemonics, toAddress, tokenId, amount } = req.body

    try {
        // Prepare transaction
        const tx = await sendTransaction(mnemonics, toAddress, tokenId, amount)
        console.log(tx)
        res.json(tx)
    } catch (e) {
        console.log('GET ERROR: \n', e);
    };
});


app.listen(port, () => console.log(`Vite-api API server running on port: ${port}`));

