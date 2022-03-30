import pkg from '@vite/vitejs';
import pkg2 from '@vite/vitejs-ws';
import pkg3 from '@vite/vitejs-http';

export { 
    createWallet, checkBalance, 
    receiveTransactions, sleep, 
    sendTransaction, 
};

const { WS_RPC } = pkg2;
const { HTTP_RPC, } = pkg3;

let WS_service = new WS_RPC("wss://node.vite.net/gvite/ws");
let HTTP_service = new HTTP_RPC("https://node.vite.net/gvite");


const { abi, error, keystore, utils, constant,
    accountBlock, ViteAPI, wallet} = pkg;
const { ReceiveAccountBlockTask } = accountBlock;

let provider = new ViteAPI(HTTP_service, () => {console.log("Connected");});



// --- CREATE WALLET ---\\
// :return: wallet insatnce object
function createWallet() {
    let w = wallet.createWallet();
    console.log('Wallet created successfully!')
    return w
}


// --- GET ACCOUNT BALANCE --- \\
// :return: Wallet balance in JSON
async function checkBalance(mnemonics) {
    // Get wallet isnatnce form mnemonics
    const wallet_ = wallet.getWallet(mnemonics);
    const { privateKey, address } = wallet_.deriveAddress(0);

    // Check balance and return
    let balance = await provider.getBalanceInfo(address);
    return balance
};

// --- UPDATE BALANCE / RECEIVE TRANSACTION --- \\
// :return: None
async function receiveTransactions(mnemonics) {
    // Get wallet isnatnce form mnemonics
    const wallet_ = wallet.getWallet(mnemonics);
    const { privateKey, address } = wallet_.deriveAddress(0);

    // Create new ReceiveTask
    const ReceiveTask = new ReceiveAccountBlockTask({
        address: address,
        privateKey: privateKey,
        provider: provider,
    });

    ReceiveTask.onSuccess((result) => {
        console.log('success', result);

        if (result.message.includes("Don't have")) {
            console.log(`stopping`)
            ReceiveTask.stop();
        };
    });
    ReceiveTask.onError((error) => {
        console.log('error', error);
    });

    // Start ReceiveTask and close when all 
    // unreceived transactions are fetched
    ReceiveTask.start({
        checkTime: 3000,
        transctionNumber: 100
    });
};


// --- SEND TRANSACTION --- \\
// :return: error or transaction data in JSON
async function sendTransaction(mnemonics, toAddress, tokenId, amount) {
    // 1. Import wallet from mnemonic/seedphrase
    const myWallet = wallet.getWallet(mnemonics);
    const { privateKey, address } = myWallet.deriveAddress(0);

    //2. Create accountBlock instance
    const { createAccountBlock } = accountBlock;
    const sendBlock = createAccountBlock('send', {
        address: address,
        toAddress: toAddress,
        tokenId: tokenId,
        amount: amount
    })

    // 3. Set provider/api and private sendBlockkey
    sendBlock.setProvider(provider).setPrivateKey(privateKey);

    // 4. Auto-fill height and previousHash
    await sendBlock.autoSetPreviousAccountBlock().catch(e => { return e });

    // 5. Get difficulty for PoW Puzzle (when not enough quota)
    const { difficulty } = await provider.request('ledger_getPoWDifficulty', {
        address: sendBlock.address,
        previousHash: sendBlock.previousHash,
        blockType: sendBlock.blockType,
        toAddress: sendBlock.toAddress,
        data: sendBlock.data
    }).catch(e => { return e });

    // If difficulty is null, it indicates the account has enough quota to 
    // send the transaction. There is no need to do PoW.
    if (difficulty) {
        // Call GVite-RPC API to calculate nonce from difficulty
        const getNonceHashBuffer = Buffer.from(sendBlock.originalAddress + sendBlock.previousHash, 'hex');
        const getNonceHash = utils.blake2bHex(getNonceHashBuffer, null, 32);
        const nonce = await provider.request('util_getPoWNonce', difficulty, getNonceHash
        ).catch(e => { return e })

        sendBlock.setDifficulty(difficulty);
        sendBlock.setNonce(nonce);
    }

    // 5. Sign and send the AccountBlock
    const result = await sendBlock.sign().send().catch(e => { return e });
    return result;
};


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// --- GET ACTIVE Subscriptions FROM DB --- \\
async function getActiveSubs() {
    let subs = await axios.get("http://localhost:8000/api/subs/?is_active=true");
    let subs_array = subs.data
    console.log(subs_array)
    return subs_array
};


// --- GET USERS --- \\
async function getUsers() {
    let users = await axios.get("http://localhost:8000/api/users");
    return users.data
};


// --- GET USER --- \\
async function getUser(id) {
    let user = await axios.get(`http://localhost:8000/api/users/?id=${id}`);
    return user.data[0]
};


// --- GET ADDRESS EVENTS FROM DB --- \\
async function getEventsForAddress(address, last) {
    let url = `http://localhost:8000/api/account_events/?address=${address}&last=${last}`
    let events = await axios.get(url);
    if (last) { return events.data[0] }
    else { return events.data };
};


// --- LISTEN FOR EVENTS --- \\
async function runListener() {
    // Fetch list of active subs from DB
    // interate through that list
    // Check if this is new account (download full event history)
    // download last 15 events(blocks) and send to DB
    // wait & repeat

    let subs = await getActiveSubs();
    subs.forEach(async sub => {
        let address = sub.vite_address
        let lastEvent = await getEventsForAddress(address, true);

        let number = 15
        if (!lastEvent) { number = 2000 };

        let blocks = await api.request('ledger_getAccountBlocksByAddress', address, 0, number);
        let blocks_array = blocks
        if (blocks_array) {
            axios.post("http://localhost:8000/api/add_account_event/", blocks_array);
        };
    });
};
// runListener()


// --- RUN PAYMENT LISTENER ---\\
async function runPaymentListener() {
    while (true) {
        let address = PAYMENT_ADDRESS
        let number = 15
        console.log(address)

        // let received_blocks = await api.request('ledger_getAccountBlocksByAddress', address, 0, number);
        let unreceived_blocks = await api.request('ledger_getUnreceivedBlocksByAddress', address, 0, number);
        // axios.post("http://localhost:8000/api/add_account_event/", received_blocks);
        console.log(unreceived_blocks)
        axios.post("http://localhost:8000/api/add_account_event/", unreceived_blocks);
        await sleep(3000);
    }
};

// runPaymentListener()
//   api.subscribe('createAccountBlockSubscriptionByAddress', viteAddress).then( (event) =>  {
//     event.on(async (result) => {
//       console.log(result[0].hash);
//       let data = await api.request('ledger_getAccountBlockByHash', result[0].hash)
//       console.log(data.address)
//     });
//     // event.off();
//   }).catch(err => {
//     console.warn(err);
//   });
// }


// --- GET TRANSACTION LIST --- \\
async function getTransactions(viteAddress) {
    let response = await api.getTransactionList({
        address: viteAddress,
        pageIndex: 0,
        pageSize: 100
    });
    console.log(response)
}
// getTransactions(address)



// --- SEND TRANSACTION --- \\
// sendAccountBlock()
// async function sendAccountBlock() {
//     // 1. Import wallet from mnemonic/seedphrase
//     const myMnemonics = 'shop shield blush kiss blade peasant card object similar music agent surprise'
//     const myWallet = wallet.getWallet(myMnemonics);
//     const { privateKey, address } = myWallet.deriveAddress(0);

//     //2. Create accountBlock instance
//     const { createAccountBlock } = accountBlock;
//     const sendBlock = createAccountBlock('send', {
//         address: address,
//         toAddress: 'vite_3302b03807d55c2673fe8db1516e90d0df0d5b1fcb7dff0b68',
//         tokenId: 'tti_f370fadb275bc2a1a839c753',
//         amount: '10000000'
//     })

//     // 3. Set provider/api and private key
//     sendBlock.setProvider(api).setPrivateKey(privateKey);

//     // 4. Auto-fill height and previousHash
//     await sendBlock.autoSetPreviousAccountBlock();

//     // 5. Sign and send the AccountBlock
//     const result = await sendBlock.sign().send();
//     return result;
// };



// balance = await checkBalance(address)
// let item = {
//   "id": 4564566,
//   "is_bot": false,
//   "username": "black",
//   "last_name": "lack",
//   "first_name": "ajha",
//   "language_code": "PL"
// }
// axios.post("http://localhost:8000/api/users/", item)

//Responsible for saving the task
// if (item.id) {
//   axios
//     .put(`http://localhost:8000/api/todos/${item.id}/`, item)
//   return;
// }