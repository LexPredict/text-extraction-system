import Task from './tasks';
import Upload from './upload';
import Notification from './notifications';
import Navigation from './navigationEvents';
import RequestStor from './request';
import * as api from '../api';

export class RootStore {
    api: any;
    upload: Upload;
    requests: RequestStor;
    notifications: Notification;
    navigation: Navigation;
    tasks: Task;    

    constructor(){
        this.api = api;
        this.requests = new RequestStor(this);
        this.upload = new Upload(this);
        this.notifications = new Notification(this);
        this.navigation = new Navigation(this);
        this.tasks = new Task(this);
    }    

    initialize(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.tasks.refresh();                
            resolve();            
        });
    }
}

export interface IStoreComponent {
    stores: RootStore;
}

export default new RootStore();