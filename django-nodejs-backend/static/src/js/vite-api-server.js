import express, { query } from 'express';
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
    // Create new Vite wallet
    const wallet = createWallet(); 

    // Create first address
    const firstAddress = wallet.deriveAddress(0);
    const { originalAddress, publicKey, privateKey, address, path } = firstAddress;
//    console.log(address);

    // Prepare response object
    const obj = {
        'mnemonics': wallet.mnemonics,
        'address': address,
    }
    res.json(obj);
});


app.post('/balance/', async (req, res) => {
    // Get balance
    const { balance, unreceived } = await checkBalance(req.body.mnemonics)
    console.log(balance, unreceived)

    if (parseInt(unreceived.blockCount)) {
        console.log('New transactions, updating...')
        await receiveTransactions(req.body.mnemonics)
        balance.pendingTransactions = true
        res.json(balance); 

    } else {
        // Return response object
        balance.pendingTransactions = false
        res.json(balance);
    };
});


app.post('/send_transaction/', async (req, res) => {
    const { mnemonics, toAddress, tokenId, amount } = req.body

    // Prepare transaction
    const tx = await sendTransaction(mnemonics, toAddress, tokenId, amount)
    console.log(tx)
    res.json(tx)
});

app.listen(port, () => console.log(`Vite-api API server running on port: ${port}`));

