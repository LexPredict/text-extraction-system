import { action, observable, runInAction, makeObservable } from 'mobx';
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

    @observable tasksPending = 0;

    defaultSortOrder = {
        'started': SortDirection.desc,
        'fileName': SortDirection.asc
    }

    
    constructor(rootStore: RootStore){
        this.rootStore = rootStore;
        // request task statuses on server each N (3) seconds        
        const refreshSecondsInterval = 3;
        setInterval(() => {
            this.refresh();            
        }, 1000 * refreshSecondsInterval);
        makeObservable(this);
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
        const requests = this.rootStore.requests.getRequests();
        if (!requests.length) {
            runInAction(() => {
                this.tasks.replace([]);
            });
            return;
        }        

        const reqIds = requests.map(r => r.id);
        const reqTimes = requests.map(r => r.started);
        const requestById = {};
        requests.forEach((r) => { requestById[r.id] = r; });
        const requestData = {
            request_ids: reqIds,
            request_times: reqTimes,
            sort_column: UploadRequestSortField[this.sortBy],
            sort_order: SortDirection[this.sortDirection],
            page_index: this.page,
            records_on_page: this.itemsOnPage
        };
        
        axios.post('api/v1/data_extraction_tasks/query_request_summary', 
            requestData, 
            {
                headers: {
                    'Content-Type': 'multipart/form-data' // 'application/json' //'multipart/form-data'
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
                this.tasksPending = response.data.tasks_pending;
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
}