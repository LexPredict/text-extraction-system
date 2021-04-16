import React, { Component } from "react"
import { inject } from 'mobx-react';
import { Button, Collapse, Form, Input, Checkbox, Select } from 'antd';
import FileUpload from "../components/FileUpload"
import { IStoreComponent } from "../store";
import styles from './PageParse.module.css'; 
import { UploadTaskSettings } from "../entity/models";


const { Panel } = Collapse;
const { Option } = Select;


type State = {
    file: File | null;
    uploadSettings: UploadTaskSettings;
}

type FileUploaderProps = {
};

@inject('stores') export class PageParse extends Component<FileUploaderProps, State> {
    fileUploaderRef: any;

    protected stores(): any {
        return (this.props as IStoreComponent).stores;
    }

    constructor(props) {
        super(props);
        this.fileUploaderRef = React.createRef();
        this.state = {
            file: null,
            uploadSettings: this.stores().tasks.restoreLastUploadTaskSettings() || new UploadTaskSettings()
        }
    }

    protected modifyState(propName: string, value: any): void {
        const newSets = { ...this.state.uploadSettings };
        const newState = { ...this.state };
        newState.uploadSettings = newSets;
        newSets[propName] = value;
        this.setState(newState);
        this.stores().tasks.saveUploadTaskSettings(newSets);
    }
    
    public onFileSelected = (file: File) => {
        const newState = {...this.state};
        newState.file = file;
        this.setState(newState);
    };

    public onUploadClicked = () => {
        if (!this.state) return;
        this.stores().upload.upload(this.state.file, this.state.uploadSettings);
        this.fileUploaderRef.current.resetFile();
    }

    render() {
        return <>
            <h2>Parse document(s)</h2>
            <form>
                <FileUpload 
                  ref={this.fileUploaderRef}
                  fileSelected={this.onFileSelected}></FileUpload>
            </form>
            <br/>

            <Collapse defaultActiveKey={['1']}>
                <Panel header="Processing settings" key="1">
                    <div>
                        <div className={styles.row}>
                            <div className={styles.column}>
                                <Form.Item
                                    label="Language"
                                    name="language"
                                    rules={[
                                        {
                                            required: false,
                                            message: 'Select document language',
                                        },
                                    ]}
                                >
                                    <Input 
                                     defaultValue={this.state.uploadSettings.language} 
                                     onChange={(e) => {this.modifyState('language', e.target.value);}} />
                                </Form.Item>
                            </div>

                            <div className={styles.column}>
                                <Form.Item
                                    label="Enable OCR"
                                    name="ocr_enable"
                                    rules={[
                                        {
                                            required: false,
                                            message: 'Enable / disable OCR',
                                        },
                                    ]}
                                >
                                    <Checkbox 
                                     onChange={(e) => {this.modifyState('ocr_enable', e.target.checked);}} 
                                     checked={this.state.uploadSettings.ocr_enable} 
                                     />
                                </Form.Item>
                            </div>

                            <div className={styles.column}>
                                <Form.Item
                                    label="Output format"
                                    name="output_format"
                                    rules={[
                                        {
                                            required: false,
                                            message: 'Output format for text metadata',
                                        },
                                    ]}
                                >
                                    <Select 
                                      defaultValue={this.state.uploadSettings.output_format} 
                                      style={{ width: 120 }}
                                      onChange={(e) => {this.modifyState('output_format', e);}}
                                      >
                                        <Option value="json">JSON</Option>
                                        <Option value="msgpack">Msgpack</Option>
                                    </Select>
                                </Form.Item>
                            </div>
                        </div>

                    </div>
                </Panel>
                <Panel header="System settings" key="2">
                    <div>
                        <div className={styles.row}>
                            <div className={styles.column}>
                                <Form.Item
                                    label="PDF conversion timeout"
                                    name="convert_to_pdf_timeout_sec"
                                    rules={[
                                        {
                                            required: false,
                                            message: 'PDF conversion timeout, seconds',
                                        },
                                    ]}
                                >
                                    <Input 
                                      defaultValue={this.state.uploadSettings.convert_to_pdf_timeout_sec} 
                                      onChange={(e) => {
                                            let nVal = parseInt(e.target.value);
                                            if (isNaN(nVal) || nVal < 0)
                                                nVal = 0;
                                            this.modifyState('convert_to_pdf_timeout_sec', nVal);
                                        }}
                                    />
                                </Form.Item>
                            </div>

                            <div className={styles.column}>
                                <Form.Item
                                    label="PDF to image timeout"
                                    name="pdf_to_images_timeout_sec"
                                    rules={[
                                        {
                                            required: false,
                                            message: 'PDF to image rendering timeout, seconds',
                                        },
                                    ]}
                                >
                                    <Input 
                                      defaultValue={this.state.uploadSettings.pdf_to_images_timeout_sec} 
                                      onChange={(e) => {
                                            let nVal = parseInt(e.target.value);
                                            if (isNaN(nVal) || nVal < 0)
                                                nVal = 0;
                                            this.modifyState('pdf_to_images_timeout_sec', nVal);
                                        }}
                                     />
                                </Form.Item>
                            </div>
                        </div>
                    </div>
                </Panel>
            </Collapse>

            <br/>

            <Button 
                type="primary" 
                onClick={() => this.onUploadClicked()}
                disabled={this.state && this.state.file ? false : true}
                >
                Upload document
            </Button>
        </> 
    }   
}