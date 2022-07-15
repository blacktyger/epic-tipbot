import {
    createWallet,
    checkBalance,
    sendTransaction,
    getTransactions,
    receiveTransactions,
} from './vite-api-wallet.js';

import _yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

/* 
NODEJS FILE WITH VITE BLOCKCHAIN API CALLS

HOW TO USE:
Execute with your script/app with arguments:
node <this_file_path> <api_call> <arg1> <arg2> etc...

COMMANDS & ARGS:
- create    no args
- balance   -m <mnemonics> -i <address_derivation_id>
- update    -m <mnemonics> -i <address_derivation_id>
- send      -m <mnemonics> -i <address_derivation_id>
            -d <destination_address> -t <tokenId> -a <amount>

*/


// Extract commands and args from console sdtin
const yargs = _yargs(hideBin(process.argv));
const args = await yargs.argv


// Recognize command and run proper function withs args
switch (args._[0]) {
    case 'create':
        await create()
        break

    case 'balance':
        await balance(args.m, args.i)
        break

    case 'update':
        await update(args.m, args.i);
        break

    case 'transactions':
        await transactions(args.a, args.n);
        break

    case 'send':
        await send(args.m, args.i, args.d, args.t, args.a);
        break

    default:
        logAndExit(1, 'invalid command')
}


/*  #########################
    ### COMMAND FUNCTIONS ### 
    #########################   */


// Send transaction
async function send(mnemonics, address_id, toAddress, tokenId, amount) {
    amount = amount.toString();

    try {
        const tx = await sendTransaction(mnemonics, address_id, toAddress, tokenId, amount)

        if ('error' in tx) {
            logAndExit(1, tx.error.message)
        } else {
            logAndExit(0, `${args._[0]} success`, tx);
        }

    } catch (error) {logAndExit(1, error)}
}


// Create new Vite wallet
async function create() {    
    try {
        // New Vite wallet
        const wallet = createWallet();

        // Create first address
        const firstAddress = wallet.deriveAddress(0);
        const { originalAddress, publicKey, privateKey, address, path } = firstAddress;

        // Prepare response object
        const data = {
            'mnemonics': wallet.mnemonics,
            'address': address
        }
        logAndExit(0, `${args._[0]} success`, data);

    } catch (error) {logAndExit(1, error)}
}


// Get wallet balance from network
async function balance(mnemonics, address_id) {
    try {
        const { balance, unreceived } = await checkBalance(mnemonics, address_id);
        balance.pending = parseInt(unreceived.blockCount);
        logAndExit(0, `${args._[0]} success`, balance);

    } catch (error) {logAndExit(1, error)}
}


// Get transactions list for address 
async function transactions(address, size=10, index=0) {
    try {
        let txs = await getTransactions(address, size, index);
        logAndExit(0, `${args._[0]} success`, txs);

    } catch (error) { logAndExit(1, error) }
}


// Update wallet balance by receiving pending transactions
async function update(mnemonics, address_id) {
    let newTransactions = 0
    try {
        // Initialize ReceiveTransaction subscribtion task
        const task = await receiveTransactions(mnemonics, address_id);

        // Handle success responses
        task.onSuccess( async (result) => {
            // If no more new transactions stop task, get last 
            // 10 transactions array for address and exit process.
            if (result.message.includes("Don't have")) {
                task.stop();
                logAndExit(0, `${args._[0]} success`, {new: newTransactions});
            } else { newTransactions += 1}
        });

        // // Handle error responses
        // task.onError((error) => {logAndExit(1, error)});

        // Start ReceiveTask and close when all 
        // unreceived transactions are processed
        task.start({
            checkTime: 1000,
            transctionNumber: 100
        });

    } catch (error) {logAndExit(1, error)}
}


// Print nested objects to stdout and exit process 
function  logAndExit(error, msg, data=null) {
    console.log(JSON.stringify(
        { error: error, msg: `${msg}`, data: data }, null, 2));
    process.exit(0);
}