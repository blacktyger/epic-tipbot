import pkg from '@vite/vitejs';
import pkg2 from '@vite/vitejs-ws';

export { 
    createWallet, checkBalance, getTransactions, 
    receiveTransactions, sendTransaction, 
};

const { WS_RPC } = pkg2;
const { utils, accountBlock, ViteAPI, wallet } = pkg;
const { ReceiveAccountBlockTask } = accountBlock;


let WS_service = new WS_RPC("wss://node.vite.net/gvite/ws");
let provider = new ViteAPI(WS_service);


// --- CREATE WALLET ---\\
// :return: wallet insatnce object
function createWallet() {
    let w = wallet.createWallet();
    console.log('Wallet created successfully!')
    return w
}


// --- GET ACCOUNT BALANCE --- \\
// :return: Wallet balance in JSON
async function checkBalance(mnemonics, address_id=0) {
    // Get wallet isnatnce form mnemonics
    const wallet_ = wallet.getWallet(mnemonics);
    const { privateKey, address } = wallet_.deriveAddress(address_id);

    // Check balance and return
    let balance = await provider.getBalanceInfo(address);
    return balance
};


// --- UPDATE BALANCE / RECEIVE TRANSACTION --- \\
// :return: None
async function receiveTransactions(mnemonics, address_id) {
    // Get wallet isnatnce form mnemonics
    const wallet_ = wallet.getWallet(mnemonics);
    const { privateKey, address } = wallet_.deriveAddress(address_id);

    // Create new ReceiveTask
    const ReceiveTask = new ReceiveAccountBlockTask({
        address: address,
        privateKey: privateKey,
        provider: provider,
    });

    return ReceiveTask
};


// --- GET TRANSACTION LIST --- \\
// :return: transactions array
async function getTransactions(viteAddress, size, index) {
    let response = await provider.getTransactionList({
        address: viteAddress,
        pageIndex: index,
        pageSize: size
    });
    return response
}


// --- SEND TRANSACTION --- \\
// :return: error or transaction data in JSON
async function sendTransaction(mnemonics, address_id=0, toAddress, tokenId, amount) {
    // 1. Import wallet from mnemonic/seedphrase
    const myWallet = wallet.getWallet(mnemonics);
    const { privateKey, address } = myWallet.deriveAddress(address_id);

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

