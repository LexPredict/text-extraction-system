import Upload from './upload';
import Notification from './notifications';
import RequestStor from './request';
import * as api from '../api';

export class RootStore {
    api: any;
    upload: Upload;
    requests: RequestStor;
    notifications: Notification;

    constructor(){
        this.api = api;
        this.requests = new RequestStor(this);
        this.upload = new Upload(this);
        this.notifications = new Notification(this);
    }    
}

export interface IStoreComponent {
    stores: RootStore;
}

export default new RootStore();