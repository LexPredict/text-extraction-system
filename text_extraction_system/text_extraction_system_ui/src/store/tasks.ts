import { action, observable, runInAction } from 'mobx';
import { RootStore } from '.';
import axios from 'axios';
import { UploadRequest, UploadTask } from '../entity/models';
import { SortDirection, UploadRequestSortField } from '../entity/enums';


export default class {
    rootStore: RootStore;

    readonly tasks = observable<UploadTask>([]);
    
    @observable page = 1;

    @observable itemsOnPage = 10;

    @observable sortBy: UploadRequestSortField = UploadRequestSortField.started;

    @observable sortDirection: SortDirection = SortDirection.desc;

    defaultSortOrder = {
        'started': SortDirection.desc,
        'fileName': SortDirection.asc
    }

    
    constructor(rootStore: RootStore){
        this.rootStore = rootStore;
    }    

    @action updatePage(page: number, itemsOnPage: number): void {
        if (page == this.page && itemsOnPage == this.itemsOnPage)
            return;
        this.page = page;
        this.itemsOnPage = itemsOnPage;
        this.refresh();
    }

    @action updateSorting(field: string, order: string) {
        const newOrder = order == 'ascend' ? SortDirection.asc : 
            order == 'descend' ? SortDirection.desc : this.defaultSortOrder[field];
        const newField = (<any>UploadRequestSortField)[field];
        if (newField == this.sortBy && newOrder == this.sortDirection)
            return;
        this.sortBy = newField;
        this.sortDirection = newOrder;
        this.refresh();
    }

    @action refresh(): void {
        let requests = this.rootStore.requests.getRequests();
        console.log(`${requests.length} tasks totally`);
        requests = this.sortAndFilterRequests(requests);
        if (!requests.length) {
            runInAction(() => {
                this.tasks.replace([]);
            });
            return;
        }        

        const reqIds = requests.map(r => r.id);
        const requestById = {};
        requests.forEach((r) => { requestById[r.id] = r; });
        
        axios.post('api/v1/data_extraction_tasks/query_request_statuses', 
            reqIds, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
        }).then((response) => {
            let newTasks = [];
            response.data.request_statuses.forEach((t) => {
                const ut: UploadTask = {
                    id: t['request_id'], 
                    status: t['status'],
                    fileName: t['original_file_name'],
                    started: requestById[t['request_id']]['started'] || new Date()
                };
                newTasks.push(ut);
            });
            newTasks = this.sortAndFilterRequests(newTasks);
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

    @action saveUploadTaskSettings(uploadSettings: any): void {
        localStorage['uploadTaskSettings'] = JSON.stringify(uploadSettings);
    }

    restoreLastUploadTaskSettings(): any {
        const setsStr = localStorage['uploadTaskSettings'];
        if (setsStr && setsStr.length)
            try {    
                return JSON.parse(setsStr);
            } catch {
                return null;
            }
        return null;
    }

    sortAndFilterRequests(requests: Array<UploadRequest>): Array<UploadRequest> {
        // this can be done on server side if we want to sort requests by the fields
        // whose values only the server knows (status, ...)
        if (!requests.length)
            return requests;
        requests.sort((a: UploadRequest, b: UploadRequest) => {
            const aVal = a[UploadRequestSortField[this.sortBy]];
            const bVal = b[UploadRequestSortField[this.sortBy]];
            const sign = aVal > bVal ? 1 : bVal > aVal ? -1 : 0;
            return this.sortDirection == SortDirection.asc ? sign : -sign;
        });
        let end = this.itemsOnPage * this.page;
        end = Math.min(end, requests.length);
        let start = end - this.itemsOnPage;
        start = Math.max(start, 0);
        return requests.slice(start, end);
    }
}