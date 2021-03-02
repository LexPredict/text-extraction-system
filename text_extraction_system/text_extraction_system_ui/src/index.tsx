import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './app/App';
import {Provider} from 'mobx-react';
import stores from './store';

//stores.settings.load().then(() => {
ReactDOM.render(
<React.StrictMode>
  <Provider stores={stores}>
    <App/>
  </Provider>
</React.StrictMode>, document.querySelector('#app'));
//});
