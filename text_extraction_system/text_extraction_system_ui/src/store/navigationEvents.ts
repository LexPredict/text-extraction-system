import { action } from 'mobx';
import { RootStore } from '.';


export default class {
    rootStore: RootStore;
    
    constructor(rootStore: RootStore){
        this.rootStore = rootStore;
    }

    @action processLocationChanged(newLocation: string): void {
        // if the user navigates to the tasks page - let's refresh the tasks
        if (newLocation.indexOf('/page-tasks') >= 0) {
            this.rootStore.tasks.refresh();
        }
    }
}