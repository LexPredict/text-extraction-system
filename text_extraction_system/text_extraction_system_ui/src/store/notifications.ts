import { action } from 'mobx';
import { RootStore } from '.';
import { notification } from "antd";


notification.config({
    placement: 'topLeft',
    bottom: 50,
    duration: 3,
    rtl: true,
  });


export default class {
    rootStore: RootStore;
    
    constructor(rootStore: RootStore){
        this.rootStore = rootStore;
    }

    @action notifyMessage(title: string, text: string | null): void {
        notification.open({
            message: title,
            description: text,
          });
    }
}