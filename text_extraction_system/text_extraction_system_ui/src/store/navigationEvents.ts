import { action, observable } from 'mobx';
import { runInNewContext } from 'vm';
import { RootStore } from '.';


export default class {
    rootStore: RootStore;

    @observable location = '/';
    
    constructor(rootStore: RootStore){
        this.rootStore = rootStore;
    }

    @action processLocationChanged(newLocation: string): void {
        this.location = newLocation;
        // if the user navigates to the tasks page - let's refresh the tasks
        if (newLocation.indexOf('/page-tasks') >= 0) {
            this.rootStore.tasks.refresh();
        }
    }
}