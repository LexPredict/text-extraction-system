import { Component } from "react"
import { inject, observer } from 'mobx-react';
import { IStoreComponent } from "../store";
import { Table, Pagination, Tag } from 'antd';
import { formatDatetime } from "../entity/utils";


type State = {
}


type EmptyProps = {
};


@inject('stores') 
@observer export class PageTasks extends Component<EmptyProps, State> {
    constructor(props) {
        super(props);
    }
   
    protected stores(): any {
        return (this.props as IStoreComponent).stores;
    }

    onPaging(page: number, itemsOnPage: number): void {
        this.stores().tasks.updatePage(page, itemsOnPage);
    }

    render() {
        const tasks = this.stores().tasks.tasks;
        const requests = this.stores().requests.getRequests();
        
        const columns = [
            {
                title: 'Request ID',
                dataIndex: 'id',
                key: 'id',
            },
            {
                title: 'Status',
                dataIndex: 'status',
                key: 'status',
                render: status => {
                    const color = status == 'DONE' ? 'green' : 'red';
                    return <Tag color={color} key={status}>
                            {status}
                      </Tag>
                },
            },
            {
                title: 'File',
                dataIndex: 'fileName',
                key: 'fileName',
            },
            {
                title: 'Started',
                dataIndex: 'started',
                key: 'started',
                render: started => {
                    return <span>{formatDatetime(started)}</span>
                }
            },
            {
                title: 'Archive',
                key: 'id',
                dataIndex: 'id',
                render: (text, record) => {
                    return <a href={`/api/v1/data_extraction_tasks/${record['id']}/results/packed_data.zip`}>.zip archive</a>
                }
            }
        ];

        return <>
            <Table dataSource={tasks.slice()} columns={columns} rowKey="id">
            </Table>
            <Pagination 
                onChange={(p, pSize) => this.onPaging(p, pSize)}
                total={requests.length}>
            </Pagination>
        </> 
    }
}