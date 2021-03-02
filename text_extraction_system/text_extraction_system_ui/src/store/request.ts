import { action } from 'mobx';
import { UploadRequest } from '../entity/models';

const requestPreffix = 'api_request_';


export default class {
    rootStore: any;
    
    constructor(rootStore){
        this.rootStore = rootStore;
    }

    getRequests(): Array<UploadRequest> {
        const requests = JSON.parse(localStorage[`${requestPreffix}list`] || '[]');
        if (!requests) return [];
        
        const reqList = [];
        requests.forEach(rId => {
            const request = JSON.parse(localStorage[`${requestPreffix}${rId}`] || 'null');
            const reqObj: UploadRequest = {
                id: rId,
                fileName: request['fileName'],
                started: new Date(request['started'])
            };
            reqList.push(reqObj);
        });
        return reqList;
    }

    @action storeRequest(request_id: string, file: File) {
        const requests = JSON.parse(localStorage[`${requestPreffix}list`] || '[]');
        requests.push(request_id);
        localStorage[`${requestPreffix}list`] = JSON.stringify(requests);
        
        localStorage[`${requestPreffix}${request_id}`] = JSON.stringify({
            fileName: file.name,
            started: new Date()
        });
    }
}