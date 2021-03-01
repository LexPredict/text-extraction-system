import { action, observable, runInAction } from 'mobx';
import { RootStore } from '.';
import axios from 'axios';
import { UploadRequest } from './request';


export class UploadTask extends UploadRequest {
    status: string;
}


export default class {
    rootStore: RootStore;

    readonly tasks = observable<UploadTask>([]);
    
    constructor(rootStore: RootStore){
        this.rootStore = rootStore;
    }

    @action refresh(): void {
        const requests = this.rootStore.requests.getRequests();
        const reqIds = requests.map(r => r.id);
        const requestById = {};
        requests.forEach((r) => { requestById[r.id] = r; });
        
        axios.post('/api/v1/data_extraction_tasks/query_request_statuses', 
            reqIds, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
        }).then((response) => {
            const newTasks = [];
            response.data.request_statuses.forEach((t) => {
                const ut: UploadTask = {
                    id: t['request_id'], 
                    status: t['status'],
                    fileName: t['original_file_name'],
                    started: requestById[t['request_id']]['started'] || new Date()
                };
                newTasks.push(ut);
            });
            runInAction(() => {
                this.tasks.replace(newTasks);
            });
        }).catch((error) => {
            if (error.response) {
              console.log(error.response.headers);
            } 
            else if (error.request) {
                console.log(error.request);
            } 
            else {
              console.log(error.message);
            }
            console.log(error.config);
        });
    }
}