import { action } from 'mobx';

const requestPreffix = 'api_request_';

export default class {
    rootStore: any;
    
    constructor(rootStore){
        this.rootStore = rootStore;
    }

    @action storeRequest(request_id: string, file: File) {
        console.log(request_id);
        console.log(localStorage[`${requestPreffix}list`]);

        const requests = JSON.parse(localStorage[`${requestPreffix}list`] || '[]');
        requests.push(request_id);
        localStorage[`${requestPreffix}list`] = JSON.stringify(requests);
        
        localStorage[`${requestPreffix}${request_id}`] = JSON.stringify({
            fileName: file.name,
            time: new Date()
        });
    }
}