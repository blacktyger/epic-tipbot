import vitejs_pkg from '@vite/vitejs';
import {connect} from './provider.js'
import {log, withTimeout} from './tools.js'

const { utils, accountBlock, wallet } = vitejs_pkg;
const { ReceiveAccountBlockTask } = accountBlock;

export {
    createWallet, getTransactions,
    receiveTransactions, sendTransaction,
    addressBalance
}

// --- CREATE WALLET ---\\
// :return: wallet instance object
function createWallet() {
    const newWallet = wallet.createWallet()
    const {address} = newWallet.deriveAddress(0)
    return {'mnemonics': newWallet.mnemonics, 'address': address}
}


// --- GET ADDRESS BALANCE --- \\
// :return: Wallet balance and unreceived blocks
async function addressBalance(address) {
    const provider = connect('wss')

    // Handle error with VITE node
    if (!provider) { throw "ERROR Connection to VITE NODE" }

    return provider.getBalanceInfo(address)
}


// --- GET TRANSACTION LIST --- \\
// :return: transactions array
async function getTransactions(address) {
    const provider = connect('wss')

    // Handle error with VITE node
    if (!provider) { throw "ERROR Connection to VITE NODE" }

    return provider.getTransactionList(address)
}


// --- UPDATE BALANCE / RECEIVE TRANSACTIONS --- \\
// :return: None
async function receiveTransactions(mnemonics, address_id, callback={}) {
    let unreceivedBlocks = []
    let successBlocks = []
    let errorBlocks = []

    // Set provider (VITE node handler)
    const provider = connect('wss', 3000)

    // Handle error with VITE node
    if (!provider) { throw "ERROR Connection to VITE NODE" }

    // Get wallet instance form mnemonics
    const wallet_ = wallet.getWallet(mnemonics);
    const {privateKey, address} = wallet_.deriveAddress(address_id);

    // Create new ReceiveTask
    const ReceiveTask = new ReceiveAccountBlockTask({
        address: address,
        privateKey: privateKey,
        provider: provider,
    });

    // Check for unreceived transactions for account
    callback.status = 'checking balance..'
    log(`Checking balance for ${address}`)
    const {balance, unreceived} = await withTimeout(addressBalance, [address], 2000)

    if (balance) {  // means if addressBalance call was success
        // Parse number of unreceivedTransactions to int
        callback.unreceived = parseInt(unreceived.blockCount)

        // Initialize ReceiveTransaction subscription task if needed
        if (callback.unreceived) {
            log(`Start Receiving ${callback.unreceived} Transactions`)
            callback.status = 'receiving transactions..'
            ReceiveTask.start({
                checkTime: 2545,
                transctionNumber: callback.unreceived
            });
        } else {
            callback.msg = `No pending transactions`
            callback.error = 1
            callback.status = "failed"
            throw Error("No pending transactions")
        }

        // Handle success callback
        ReceiveTask.onSuccess((result) => {
            log({success: successBlocks.length, error: errorBlocks.length})

            if (result.message.includes("Don't have")) {
                // Handle last unreceived transaction and finish task
                let data = {unreceived: callback.unreceived, success: successBlocks, error: errorBlocks}
                callback.msg = "finished " + callback.unreceived + " unreceived blocks"
                callback.data = data
                callback.status = 'success'
                ReceiveTask.stop();
                log(data)

            } else {
                // Update callback status and keep receiving
                callback.msg = "transaction " + (unreceivedBlocks.length + 1) + "/" + callback.unreceived
                log(`${unreceivedBlocks.length + 1} / ${callback.unreceived}`, result.message)
                unreceivedBlocks.push(result.message)
                successBlocks.push(result.message)
            }
        });

        // Handle error responses
        ReceiveTask.onError((error) => {
            try {
                errorBlocks.push(error.error.error.message)
            } catch (e) {
                errorBlocks.push(error.error.message)
            }
        });

    } else {
        // Handle custom timeout case
        callback.msg = `Connection timeout`
        callback.error = 1
        callback.status = "failed"
        throw Error("Connection timeout")
    }
}


// --- SEND TRANSACTION --- \\
// :return: error or transaction data in JSON
async function sendTransaction(mnemonics, address_id, toAddress, tokenId, amount) {
    // Connect to provider (VITE node handler)
    const provider = connect('wss', 2000)

    // Handle error with VITE node
    if (!provider) { throw "ERROR Connection to VITE NODE" }

    // 1. Import wallet from mnemonic/seedphrase
    const myWallet = wallet.getWallet(mnemonics);
    const { privateKey, address } = myWallet.deriveAddress(address_id);

    //2. Create accountBlock instance
    const {createAccountBlock} = accountBlock;
    const sendBlock = createAccountBlock('send', {
        address: address,
        toAddress: toAddress,
        tokenId: tokenId,
        amount: amount
    })

    // 3. Set provider and private sendBlockKey
    sendBlock.setProvider(provider).setPrivateKey(privateKey);

    // 4. Autofill height and previousHash
    await sendBlock.autoSetPreviousAccountBlock().catch(e => {throw e.message});

    // 5. Get difficulty for PoW Puzzle (when not enough quota)
    const {difficulty} = await provider.request('ledger_getPoWDifficulty', {
        address: sendBlock.address,
        previousHash: sendBlock.previousHash,
        blockType: sendBlock.blockType,
        toAddress: sendBlock.toAddress,
        data: sendBlock.data
    }).catch(e => {throw e.message});

    // If difficulty is null, it indicates the account has enough quota to
    // send the transaction. There is no need to do PoW.
    if (difficulty) {
        // Call GVite-RPC API to calculate nonce from difficulty
        const getNonceHashBuffer = Buffer.from(sendBlock.originalAddress + sendBlock.previousHash, 'hex');
        const getNonceHash = utils.blake2bHex(getNonceHashBuffer, null, 32);
        const nonce = await provider.request('util_getPoWNonce', difficulty, getNonceHash
        ).catch(e => {throw e.message})

        sendBlock.setDifficulty(difficulty);
        sendBlock.setNonce(nonce);
    }

    // 6. Sign and send the AccountBlock
    return sendBlock.sign().send().catch(e => {throw e.message});
}


