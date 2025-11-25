import React, { useState, useEffect } from "react";
import { FixedSizeList as List, ListChildComponentProps } from "react-window";
import { DocumentQueueAdd20Regular, DocumentPdfRegular, ImageRegular } from "@fluentui/react-icons";
import { TableCellActions, Tooltip, Button } from "@fluentui/react-components";
import {
    PresenceBadgeStatus, Avatar, useScrollbarWidth, useFluent, TableBody, TableCell, TableRow, Table,
    TableHeader, TableHeaderCell, TableCellLayout, TableSelectionCell, createTableColumn, useTableFeatures,
    useTableSelection, useTableSort, TableColumnId, useTableColumnSizing_unstable,
    TableRowId
} from "@fluentui/react-components";
import './ProcessQueueGrid.styles.scss';
import AutoSizer from "react-virtualized-auto-sizer";
import CustomCellRender from "./CustomCellRender";
import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { RootState, AppDispatch } from '../../../../store';
import { setSelectedGridRow, deleteProcessedFile, bulkDeleteProcessedFiles } from '../../../../store/slices/leftPanelSlice';
import useFileType from "../../../../Hooks/useFileType";
import { Confirmation } from "../../../../Components/DialogComponent/DialogComponent.tsx";
import { Item, TableRowData, ReactWindowRenderFnProps, GridComponentProps, ProcessedFileResponse } from './ProcessQueueGridTypes.ts';

const columns = [
    createTableColumn<Item>({
        columnId: "fileName",
        compare: (a, b) => {
            return a.fileName.label.localeCompare(b.fileName.label);
        },
    }),
    createTableColumn<Item>({
        columnId: "imported",
        compare: (a, b) => {
            const dateA = new Date(a.imported.label).getTime();
            const dateB = new Date(b.imported.label).getTime();
            return dateA - dateB; // Ascending order (oldest to newest)
        },
    }),
    createTableColumn<Item>({
        columnId: "status",
        compare: (a, b) => {
            return a.status.label.localeCompare(b.status.label);
        },
        renderHeaderCell: () => <><div className="centerAlign">Status</div></>,
    }),
    // createTableColumn<Item>({
    //     columnId: "processTime",
    //     compare: (a, b) => {
    //         return a.processTime.label.localeCompare(b.processTime.label);
    //     },
    // }),
    createTableColumn<Item>({
        columnId: "entityScore",
        compare: (a, b) => {
            return a.entityScore.label.localeCompare(b.entityScore.label);
        },
    }),
    createTableColumn<Item>({
        columnId: "schemaScore",
        compare: (a, b) => {
            return a.schemaScore.label.localeCompare(b.schemaScore.label);
        },
    }),
    createTableColumn<Item>({
        columnId: "folder",
        compare: (a, b) => {
            const folderA = a.folder.label || "";
            const folderB = b.folder.label || "";
            return folderA.localeCompare(folderB);
        },
    }),
    createTableColumn<Item>({
        columnId: "processId",
        compare: (a, b) => {
            return a.processId.label.localeCompare(b.processId.label);
        },
    }),
];


const ProcessQueueGrid: React.FC<GridComponentProps> = () => {

    const dispatch = useDispatch<AppDispatch>();
    const store = useSelector((state: RootState) => ({
        gridData: state.leftPanel.gridData,
        processId: state.leftPanel.processId,
        deleteFilesLoader: state.leftPanel.deleteFilesLoader,
        pageSize: state.leftPanel.pageSize,
        gridLoader: state.leftPanel.gridLoader
    }), shallowEqual
    );

    const { targetDocument } = useFluent();
    const scrollbarWidth = useScrollbarWidth({ targetDocument });

    const [sortState, setSortState] = useState<{
        sortDirection: "ascending" | "descending";
        sortColumn: TableColumnId | undefined;
    }>({
        sortDirection: "ascending" as const,
        sortColumn: "file",
    });

    const [items, setItems] = useState<Item[]>([]); // State to store fetched items
    const [filteredItems, setFilteredItems] = useState<Item[]>([]); // State for filtered items
    const { fileType, getMimeType } = useFileType(null);

    const folderFilter = useSelector((state: RootState) =>
        state.leftPanel.folderFilter.selectedFolders
    );

    const [selectedRows, setSelectedRows] = React.useState(
        () => new Set<TableRowId>()
    );

    const [isDialogOpen, setIsDialogOpen] = React.useState(false);
    const [selectedDeleteItem, setSelectedDeleteItem] = useState<Item | null>(null);

    const [isBulkDeleteDialogOpen, setIsBulkDeleteDialogOpen] = React.useState(false);

    useEffect(() => {
        const getFIleImage = (mimeType: any, file: any) => {
            if (mimeType === "application/pdf") return <DocumentPdfRegular />
            const mType = getMimeType({ name: file });
            switch (mType) {
                case 'image/jpeg':
                case 'image/png':
                case 'image/gif':
                case 'image/bmp':
                    return <ImageRegular />
                case 'application/pdf':
                    return <DocumentPdfRegular />
                default:
                    return <DocumentQueueAdd20Regular />
            }
        }
        if (!store.gridLoader) {
            if (store.gridData.items.length > 0) {
                const items = store.gridData.items.map((item: ProcessedFileResponse) => ({
                    fileName: {
                        label: item.processed_file_name,
                        icon: getFIleImage(item.processed_file_mime_type, item.processed_file_name)
                    },
                    imported: { label: item.imported_time },
                    status: { label: item.status },
                    // processTime: { label: item.processed_time ?? "..." },
                    entityScore: { label: item.entity_score.toString() },
                    schemaScore: { label: item.schema_score.toString() },
                    processId: { label: item.process_id },
                    lastModifiedBy: { label: item.last_modified_by },
                    file_mime_type: { label: item.processed_file_mime_type || '' },
                    confidence: {
                        totalFields: item.confidence?.totalFields || 0,
                        zeroConfidenceCount: item.confidence?.zeroConfidenceCount || 0,
                        zeroConfidenceFields: item.confidence?.zeroConfidenceFields || []
                    },
                    folder: { label: item.folder || null },
                }));
                setItems(items);
            } else {
                setItems([])
                dispatch(setSelectedGridRow({ processId: '', item: {}}));
            }
        }

    }, [store.gridData])

    // Apply folder filtering
    useEffect(() => {
        if (!folderFilter || folderFilter.length === 0) {
            // No filter - show all items
            setFilteredItems(items);
            return;
        }

        const filtered = items.filter(item => {
            const folderValue = item.folder.label;

            // Handle "(Unassigned)" filter selection
            if (folderFilter.includes('(Unassigned)')) {
                if (!folderValue || folderValue === null || folderValue === '') {
                    return true;
                }
            }

            // Check if item's folder is in selected folders
            if (folderValue && folderFilter.includes(folderValue)) {
                return true;
            }

            return false;
        });

        setFilteredItems(filtered);
    }, [items, folderFilter]);

    useEffect(() => {
        // For multiselect: only update selected grid row when exactly one row is selected
        if (items.length > 0 && selectedRows.size === 1) {
            const selectedRow = [...selectedRows][0];
            if (typeof selectedRow === 'number') {
                let selectedItem = items[selectedRow];
                if (selectedItem) {
                    const findItem = getSelectedItem(selectedItem?.processId.label ?? '');
                    dispatch(setSelectedGridRow({ processId: selectedItem?.processId.label, item: findItem }));
                }
            }
        } else if (selectedRows.size === 0) {
            // Clear selection when no rows selected
            dispatch(setSelectedGridRow({ processId: '', item: {}}));
        }
        // When multiple rows selected, don't update the detail panel
    }, [selectedRows, items])

    const getSelectedItem = (processId: string) => {
        const findItem = store.gridData.items.find((item: any) => item.process_id == processId)
        return findItem;
    }

    const {
        getRows,
        sort: { getSortDirection, toggleColumnSort, sort },
        selection: {
            allRowsSelected,
            someRowsSelected,
            toggleAllRows,
            toggleRow,
            isRowSelected,
        },
    } = useTableFeatures(
        {
            columns,
            items: filteredItems,
        },
        [
            useTableSelection({
                selectionMode: "multiselect",
                selectedItems: selectedRows,
                onSelectionChange: (e, data) => {
                    setSelectedRows(data.selectedItems)
                },
            }),
            useTableSort({
                sortState,
                onSortChange: (e, nextSortState) => setSortState(nextSortState),
            }),
        ]
    );



    const rows: TableRowData[] = sort(getRows((row) => {
        const selected = isRowSelected(row.rowId);
        return {
            ...row,
            onClick: (e: React.MouseEvent) => {
                // Don't trigger selection on row click - only for review purposes
                // Selection only happens via checkbox
            },
            onKeyDown: (e: React.KeyboardEvent) => {
                // Don't trigger selection on keyboard - only via checkbox
            },
            selected,
            appearance: selected ? "brand" : "none",
        };
    }));

    const onClickCellActions = (e: React.MouseEvent<HTMLDivElement>) =>
        e.preventDefault();
    const onKeyDownCellActions = (e: React.KeyboardEvent<HTMLDivElement>) =>
        e.key === " " && e.preventDefault();

    const isDeleteDisabled = (processId: string, status: string) => {
        if (status != 'Completed' && status != 'Error') return { disabled: true, message: 'Inprogress' }
        if (store.deleteFilesLoader.includes(processId)) return { disabled: true, message: 'Deleting' }
        return { disabled: false, message: '' }
    };

    const RenderRow = ({ index, style, data }: ReactWindowRenderFnProps) => {
        const { item, selected, appearance } = data[index];
        const deleteBtnStatus = isDeleteDisabled(item.processId.label, item.status.label);

        // Handle row click - set selected row for review (not for deletion)
        const handleRowClick = (e: React.MouseEvent) => {
            const target = e.target as HTMLElement;
            // Don't handle clicks on checkbox, buttons, or menu items
            const isInteractiveElement =
                target.closest('[role="checkbox"]') ||
                target.closest('button') ||
                target.closest('[role="menuitem"]') ||
                target.closest('[role="menu"]');

            if (!isInteractiveElement && !e.defaultPrevented) {
                // Set this row as selected for review purposes only
                const findItem = getSelectedItem(item.processId.label);
                dispatch(setSelectedGridRow({ processId: item.processId.label, item: findItem }));
            }
        };

        return (
            <TableRow
                aria-rowindex={index + 2}
                style={style}
                key={item.processId.label}
                aria-selected={selected}
                onClick={handleRowClick}
                appearance={appearance}
            >
                <TableSelectionCell checked={selected} aria-label={`Select ${item.fileName.label}`} />
                <TableCell className="col col1">
                    <Tooltip content={item.fileName.label} relationship="label">
                        <TableCellLayout truncate media={item.fileName.icon}>
                            {item.fileName.label}
                        </TableCellLayout>
                    </Tooltip>
                </TableCell>
                <TableCell className="col col2">
                    <CustomCellRender type="date" props={{ text: item.imported.label }} />
                </TableCell>
                <TableCell className="col col3">
                    <CustomCellRender type="roundedButton" props={{ txt: item.status.label }} />
                </TableCell>
                {/* <TableCell className="col col4">
                    <CustomCellRender type="processTime" props={{ timeString: item.processTime.label }} />
                </TableCell> */}

                <TableCell className="col col4">
                    <CustomCellRender type="percentage" props={{ valueText: item.entityScore.label, status: item.status.label }} />
                </TableCell>
                <TableCell className="col col5">
                    <CustomCellRender type="schemaScore" props={{
                        valueText: item.schemaScore.label,
                        lastModifiedBy: item.lastModifiedBy.label,
                        status: item.status.label,
                        confidence: item.confidence
                    }} />
                </TableCell>
                <TableCell className="col col6">
                    <CustomCellRender type="text" props={{ text: item.folder.label || "-" }} />
                </TableCell>
                <TableCell className="col col7" onClick={onClickCellActions} onKeyDown={onKeyDownCellActions}>
                    <CustomCellRender
                        type="deleteButton"
                        props={{
                            item: item,
                            deleteBtnStatus: deleteBtnStatus,
                            setSelectedDeleteItem: setSelectedDeleteItem,
                            toggleDialog: toggleDialog,
                        }}
                    />
                </TableCell>
            </TableRow>
        );
    };

    const headerSortProps = (columnId: TableColumnId) => ({
        onClick: (e: React.MouseEvent) => toggleColumnSort(e, columnId),
        sortDirection: getSortDirection(columnId),
    });

    const handleDelete = async () => {
        if (!selectedDeleteItem) {
            return;
        }

        try {
            // Close dialog first
            toggleDialog();

            // Wait for delete operation to complete
            const result = await dispatch(
                deleteProcessedFile({ processId: selectedDeleteItem.processId.label ?? null })
            ).unwrap();

            // Success toast is handled in slice (line 272)
            // Clear selection after successful delete
            setSelectedDeleteItem(null);
        } catch (error: any) {
            // Error toast is handled in slice (line 282)
            // Log error for debugging
            console.error('[ProcessQueueGrid] Delete failed:', error);
        }
    };

    const toggleDialog = () => {
        setIsDialogOpen(!isDialogOpen);
    };

    const dialogContnet = () => {
        return (
            <p>Are you sure you want to delete this file?</p>
        )
    }

    const handleBulkDelete = async () => {
        const selectedProcessIds = Array.from(selectedRows)
            .filter((rowId): rowId is number => typeof rowId === 'number')
            .map(rowId => items[rowId].processId.label);

        if (selectedProcessIds.length === 0) {
            return;
        }

        try {
            // Close dialog first
            toggleBulkDeleteDialog();

            // Wait for bulk delete operation to complete
            const result = await dispatch(
                bulkDeleteProcessedFiles({ processIds: selectedProcessIds })
            ).unwrap();

            // Success/error toasts are handled in slice (lines 303, 307)
            // Clear selection after operation
            setSelectedRows(new Set());
        } catch (error: any) {
            // Error toast is handled in slice (line 317)
            // Log error for debugging
            console.error('[ProcessQueueGrid] Bulk delete failed:', error);
            // Keep selection in case user wants to retry
        }
    };

    const toggleBulkDeleteDialog = () => {
        setIsBulkDeleteDialogOpen(!isBulkDeleteDialogOpen);
    };

    const bulkDeleteDialogContent = () => {
        const count = selectedRows.size;
        return (
            <p>Are you sure you want to delete {count} selected file{count > 1 ? 's' : ''}?</p>
        )
    }

    const isBulkDeleteDisabled = () => {
        if (selectedRows.size === 0) return true;

        // Check if any selected item is in progress
        const selectedItems = Array.from(selectedRows)
            .filter((rowId): rowId is number => typeof rowId === 'number')
            .map(rowId => items[rowId]);

        return selectedItems.some(item => {
            const status = item.status.label;
            return status !== 'Completed' && status !== 'Error';
        });
    };

    return (
        <>
            <div className="gridContainer">
                {selectedRows.size > 0 && (
                    <div style={{ padding: '10px', borderBottom: '1px solid #e0e0e0' }}>
                        <Button
                            appearance="primary"
                            disabled={isBulkDeleteDisabled()}
                            onClick={toggleBulkDeleteDialog}
                        >
                            Delete Selected ({selectedRows.size})
                        </Button>
                    </div>
                )}
                <Table
                    noNativeElements={true}
                    sortable
                    size="medium"
                    aria-label="Table with selection"
                    aria-rowcount={rows.length}
                    className="gridTable"
                >
                    <TableHeader>
                        <TableRow aria-rowindex={1}>
                            <TableSelectionCell
                                checked={
                                    allRowsSelected
                                        ? true
                                        : someRowsSelected
                                        ? "mixed"
                                        : false
                                }
                                onClick={toggleAllRows}
                            />
                            <TableHeaderCell className="col col1" {...headerSortProps("fileName")}>File name</TableHeaderCell>
                            <TableHeaderCell className="col col2"  {...headerSortProps("imported")}>Imported</TableHeaderCell>
                            <TableHeaderCell className="col col3"  {...headerSortProps("status")}>Status</TableHeaderCell>
                            {/* <TableHeaderCell className="col col4" {...headerSortProps("processTime")}>Process time</TableHeaderCell> */}
                            <TableHeaderCell className="col col4" {...headerSortProps("entityScore")}>Entity score</TableHeaderCell>
                            <TableHeaderCell className="col col5" {...headerSortProps("schemaScore")}>Schema score</TableHeaderCell>
                            <TableHeaderCell className="col col6" {...headerSortProps("folder")}>Folder</TableHeaderCell>
                            <TableHeaderCell className="col col7" ></TableHeaderCell>
                            {/* <div role="presentation" style={{ width: scrollbarWidth }} /> */}
                        </TableRow>
                    </TableHeader>
                    <TableBody className="gridTableBody">
                        <div className="GridList">
                            {rows.length > 0? 
                            <AutoSizer>
                                {({ height, width }) => (
                                    <List
                                        height={height}
                                        itemCount={filteredItems.length}
                                        itemSize={45}
                                        width="100%"
                                        itemData={rows}
                                    >
                                        {RenderRow}
                                    </List>
                                )}
                            </AutoSizer> : 
                            <p style={{ textAlign: 'center' }}>No data available</p>
                            }
                        </div>
                    </TableBody>
                </Table>
            </div>

            <Confirmation
                title="Delete Confirmation"
                content={dialogContnet()}
                isDialogOpen={isDialogOpen}
                onDialogClose={toggleDialog}
                footerButtons={[
                    {
                        text: "Confirm",
                        appearance: "primary",
                        onClick: handleDelete,
                    },
                    {
                        text: "Cancel",
                        appearance: "secondary",
                        onClick: toggleDialog,
                    }
                ]}
            />

            <Confirmation
                title="Bulk Delete Confirmation"
                content={bulkDeleteDialogContent()}
                isDialogOpen={isBulkDeleteDialogOpen}
                onDialogClose={toggleBulkDeleteDialog}
                footerButtons={[
                    {
                        text: "Confirm",
                        appearance: "primary",
                        onClick: handleBulkDelete,
                    },
                    {
                        text: "Cancel",
                        appearance: "secondary",
                        onClick: toggleBulkDeleteDialog,
                    }
                ]}
            />
        </>
    );
};

export default ProcessQueueGrid;