import { Component } from "react"
import { inject, observer } from 'mobx-react';
import { IStoreComponent } from "../store";
import { Table, Pagination, Tag } from 'antd';


@inject('stores') 
@observer export class PageTasks extends Component {
   
    protected stores(): any {
        return (this.props as IStoreComponent).stores;
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
                    return <span>{this.formatDatetime(started)}</span>
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
            <Table dataSource={tasks.slice()} columns={columns} key="id">
            </Table>
            <Pagination onChange={(p, pSize) => {console.log(p + ': ' + pSize)}} total={requests.length}>
            </Pagination>
        </> 
    }

    formatDatetime(m: Date): string  {
        return m.getUTCFullYear() + "/" + 
          (m.getUTCMonth()+1) + "/" + 
          m.getUTCDate() + " " + 
          m.getUTCHours() + ":" + m.getUTCMinutes() + ":" + m.getUTCSeconds();
    }
}