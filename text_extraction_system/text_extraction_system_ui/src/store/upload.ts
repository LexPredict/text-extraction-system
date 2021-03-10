import axios from 'axios';
import { action } from 'mobx';
import { RootStore } from '.';
import { UploadTaskSettings } from '../entity/models';


export default class {
    rootStore: RootStore;
    
    constructor(rootStore: RootStore){
        this.rootStore = rootStore;
    }

    @action upload(file: File, settings: UploadTaskSettings): void {
        const formData = new FormData();
        formData.append('file', file);
        for (const key in settings)
            formData.append(key, settings[key]);

        axios.post('api/v1/data_extraction_tasks/', 
            formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        }).then((response) => {
            if (typeof response.data === 'string' || response.data instanceof String) {
                const requestId = response.data;
                this.rootStore.requests.storeRequest(requestId as string, file);
                this.rootStore.notifications.notifyMessage(`file "${file.name}" is uploaded`, null);
            }
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