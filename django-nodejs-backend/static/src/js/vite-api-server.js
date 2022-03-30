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
    console.log(address);

    // Prepare response object
    const obj = {
        'mnemonics': wallet.mnemonics,
        'address': address,
    }
    res.json(obj);
});


app.post('/balance/', async (req, res) => {
    // Get body from POST rquest
    console.log(req.body.mnemonics)

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
    console.log(typeof mnemonics, typeof toAddress, typeof tokenId, typeof amount)

    // Prepare transaction
    const tx = await sendTransaction(mnemonics, toAddress, tokenId, amount)
    console.log(tx)
    res.json(tx)
});



// mnemonics = query.mnemonics, query.toAddress, query.tokenId, query.amount


// app.post('/book', (req, res) => {
//     const book = req.body;

//     // output the book to the console for debugging
//     console.log(book);
//     books.push(book);

//     res.send('Book is added to the database');
// });

// app.get('/book/:isbn', (req, res) => {
//     // reading isbn from the URL
//     const isbn = req.params.isbn;

//     // searching books for the isbn
//     for (let book of books) {
//         if (book.isbn === isbn) {
//             res.json(book);
//             return;
//         }
//     }

//     // sending 404 when not found something is a good practice
//     res.status(404).send('Book not found');
// });

// app.delete('/book/:isbn', (req, res) => {
//     // reading isbn from the URL
//     const isbn = req.params.isbn;

//     // remove item from the books array
//     books = books.filter(i => {
//         if (i.isbn !== isbn) {
//             return true;
//         }

//         return false;
//     });

//     // sending 404 when not found something is a good practice
//     res.send('Book is deleted');
// });

// app.post('/book/:isbn', (req, res) => {
//     // reading isbn from the URL
//     const isbn = req.params.isbn;
//     const newBook = req.body;

//     // remove item from the books array
//     for (let i = 0; i < books.length; i++) {
//         let book = books[i]

//         if (book.isbn === isbn) {
//             books[i] = newBook;
//         }
//     }

//     // sending 404 when not found something is a good practice
//     res.send('Book is edited');
// });

app.listen(port, () => console.log(`Vite-api API server running on port: ${port}`));

