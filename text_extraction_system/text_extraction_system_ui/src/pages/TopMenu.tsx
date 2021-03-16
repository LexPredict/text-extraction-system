import { Menu, Badge, Button } from 'antd';
import { Component } from 'react';
import { Link } from 'react-router-dom';
import React from 'react';
import { inject, observer } from 'mobx-react';
import styles from './TopMenu.module.css'; 
import { IStoreComponent } from '../store';

export class MenuItem {
    name: string;
    title?: string;
    url: string;
    children: Array<MenuItem>;
    showPendingTasks: boolean;
    
    constructor(
        name: string,
        title: string,
        url: string,
        showPendingTasks?: boolean,
        children?: Array<MenuItem>) {
            this.name = name;
            this.title = title;
            this.url = url;
            this.showPendingTasks = showPendingTasks || false;
            this.children = children || Array<MenuItem>();
        }
}

interface TopMenuProps { // extends IStoreComponent {
  rows: MenuItem[]
}

interface TopMenuPropsWithStores extends TopMenuProps, IStoreComponent {
}

@inject('stores') 
@observer export class TopMenu extends Component<TopMenuPropsWithStores> {
    constructor(props: TopMenuPropsWithStores) {
        super(props);
    }

    protected stores(): any {
        return (this.props as IStoreComponent).stores;
    }
  
    render() {
        const path = window.location.pathname;
        let pageIndex = 0;
        this.props.rows.forEach((r, i) => {
            if (path.indexOf(r.url) >= 0) pageIndex = i;
        });
        const tasks = this.stores().tasks.tasksPending;

        return <>
            <Menu
                theme="light"
                mode="horizontal"
                defaultSelectedKeys={[`${pageIndex + 1}`]}
                style={{ lineHeight: '64px' }}
                collapsedWidth="0">
                                            
                {this.props.rows.map((item, i) =>
                    <Menu.Item title={item.title} key={i+1}>
                        <Badge 
                          className={styles.badge_spaced} 
                          count={item.showPendingTasks ? tasks : 0}
                          >
                            <Link to={item.url}>
                                <span>{item.name}</span>
                            </Link>
                        </Badge>                        
                    </Menu.Item>
                )}
            </Menu>
        </> 
    }   
}