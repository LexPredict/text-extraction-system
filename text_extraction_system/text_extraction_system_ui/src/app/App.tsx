import './App.css';
import { TopMenu, MenuItem } from '../pages/TopMenu';
import { BrowserRouter, Switch, Route } from 'react-router-dom'
import { PageParse } from '../pages/PageParse';
import { PageTasks } from '../pages/PageTasks';
import { useHistory } from 'react-router-dom';
import { useEffect } from 'react';
import { inject } from 'mobx-react';
import { IStoreComponent } from "../store";
import { Component } from "react"


@inject('stores') export class App extends Component {
   
    protected stores(): any {
        return (this.props as IStoreComponent).stores;
    }

    render() {
      const subdir = process.env.UI_SUB_DIR || '';

      return <>
          <BrowserRouter basename={subdir}>
            <AppRouter 
              locationChanged={() => {this.stores().navigation.processLocationChanged(location.pathname)}}
              >
            </AppRouter>
          </BrowserRouter>
      </>
    }   
}


interface LocationChangedProps {
  locationChanged: (newLocation: string) => void;
}


export const AppRouter: React.FC<LocationChangedProps> = (props: LocationChangedProps) => {
  const menuItems = [
    new MenuItem("Parse", "Upload and parse files", "/"),
    new MenuItem("Tasks", "Completed parsing tasks", "/page-tasks"),
  ];

  const history = useHistory();
  useEffect(() => {
      return history.listen((location) => {
        props.locationChanged(location.pathname);
      }) 
  },[history]);

  return (
      <div className="App">
        <TopMenu rows={menuItems} />
        <Switch>
          <Route path="/page-tasks">
            <PageTasks />
          </Route>
          <Route path="/">
            <PageParse />
          </Route>
        </Switch>
      </div>
  );
};

export default App;