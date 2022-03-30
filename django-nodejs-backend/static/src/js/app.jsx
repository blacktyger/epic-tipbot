import React, { Component } from "react";
import axios from "axios";

import './App.css'


class App extends Component {
  state = {
    buttonText: 'Create Wallet :)',
    mnemonic: '',
    count: 0,
};

  render () {
    return (
      <div className="App">
        <header className="App-header">
          <p>Hello Vite + React!</p>
          <p>
            <button type="button" onClick={() => this.state.count = 1}>
              count is: {this.state.count}
            </button>
            <br />
            <button id="createBtn" type="button" onClick={() => createWallet()}>
              {this.state.buttonText}
              {this.state.mnemonic}
            </button>
          </p>
          <p>
            Edit <code>App.jsx</code> and save to test HMR updates.
          </p>
          <p>
            <a
              className="App-link"
              href="https://reactjs.org"
              target="_blank"
              rel="noopener noreferrer"
            >
              Learn React
            </a>
            {' | '}
            <a
              className="App-link"
              href="https://vitejs.dev/guide/features.html"
              target="_blank"
              rel="noopener noreferrer"
            >
              Vite Docs
            </a>
          </p>
        </header>
      </div>
    )}
}

export default App
