import './App.css';
import { TopMenu, MenuItem } from '../pages/TopMenu';
import { BrowserRouter, Switch, Route } from 'react-router-dom'
import { PageParse } from '../pages/PageParse';
import { PageLog } from '../pages/PageLog';

function App() {
  const menuItems = [
    new MenuItem("Parse", "Upload and parse files", "/"),
    new MenuItem("Log", "Completed parsing tasks", "/page-log"),
  ];

  return (
      <div className="App">
        <BrowserRouter>
          <TopMenu rows={menuItems} />
          <Switch>
            <Route path="/page-log">
              <PageLog />
            </Route>
            <Route path="/">
              <PageParse />
            </Route>
          </Switch>
        </BrowserRouter>
      </div>
  );
}

export default App;