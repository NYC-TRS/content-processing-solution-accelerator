import React, { useState, useEffect } from "react";
import { Button } from "@fluentui/react-components";
import { ArrowClockwiseRegular, ArrowUploadRegular, ArrowDownloadRegular, ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled, bundleIcon } from "@fluentui/react-icons";
import PanelToolbar from "../../Hooks/usePanelHooks.tsx";
import ProcessQueueGrid from './Components/ProcessQueueGrid/ProcessQueueGrid.tsx';
import SchemaDropdown from './Components/SchemaDropdown/SchemaDropdown';
import UploadFilesModal from "../../Components/UploadContent/UploadFilesModal.tsx";

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { fetchSchemaData, fetchContentTableData, setRefreshGrid, fetchSwaggerData } from '../../store/slices/leftPanelSlice.ts';
import { AppDispatch, RootState } from '../../store/index.ts';
import { startLoader, stopLoader } from "../../store/slices/loaderSlice.ts";
import { toast } from "react-toastify";
import { exportToExcel, exportBulkResultsToExcel } from '../../utils/excelExport';
import httpUtility from '../../Services/httpUtility';

const ChevronDoubleLeft = bundleIcon(ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled);

interface PanelLeftProps {
  togglePanel: (panel: string) => void;
}

const PanelLeft: React.FC<PanelLeftProps> = ({ togglePanel }) => {

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBulkExporting, setIsBulkExporting] = useState(false);
  const dispatch = useDispatch<AppDispatch>();

  const store = useSelector((state: RootState) => ({
    schemaSelectedOption: state.leftPanel.schemaSelectedOption,
    page_size: state.leftPanel.gridData.page_size,
    pageSize: state.leftPanel.pageSize,
    isGridRefresh: state.leftPanel.isGridRefresh,
    gridData: state.leftPanel.gridData,
  }), shallowEqual);

  useEffect(() => {
    const fetchData = async () => {
      try {
        dispatch(startLoader("1"));
        await Promise.allSettled([
          dispatch(fetchSwaggerData()).unwrap(),
          dispatch(fetchSchemaData()).unwrap(),
          dispatch(fetchContentTableData({
            pageSize: store.pageSize,
            pageNumber: 1,
            schemaId: store.schemaSelectedOption?.Id
          })).unwrap(),
        ]);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        dispatch(stopLoader("1"));
      }
    };
    fetchData();

  }, [dispatch]);

  useEffect(() => {
    if (store.isGridRefresh) {
      refreshGrid();
    }
  }, [store.isGridRefresh, dispatch]);

  // Auto-refresh grid when schema selection changes
  useEffect(() => {
    if (store.schemaSelectedOption?.Id) {
      refreshGrid();
    }
  }, [store.schemaSelectedOption?.Id]);

  const refreshGrid = async () => {
    try {
      dispatch(startLoader("1"));
      await dispatch(fetchContentTableData({
        pageSize: store.pageSize,
        pageNumber: 1,
        schemaId: store.schemaSelectedOption?.Id
      })).unwrap()
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      dispatch(stopLoader("1"));
      dispatch(setRefreshGrid(false));
    }
  }

  const handleImportContent = () => {
    const { schemaSelectedOption } = store;
    if (Object.keys(schemaSelectedOption).length === 0) {
      toast.error("Please Select Schema");
      return;
    }
    setIsModalOpen(true);
  };

  const handleExportToExcel = () => {
    const { gridData } = store;
    if (!gridData.items || gridData.items.length === 0) {
      toast.warning("No data available to export");
      return;
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const fileName = `ProcessedDocuments_${timestamp}.xlsx`;

    exportToExcel(gridData.items, fileName);
    toast.success(`Exported ${gridData.items.length} records to Excel`);
  };

  const handleBulkExportAllResults = async () => {
    const { gridData, schemaSelectedOption } = store;
    const schemaName = schemaSelectedOption?.Description || "all schemas";

    if (!gridData.items || gridData.items.length === 0) {
      toast.warning("No data available to export");
      return;
    }

    // Filter out documents that are not in "Completed" state
    const processedDocuments = gridData.items.filter(item =>
      item.status.toLowerCase() === 'completed'
    );

    if (processedDocuments.length === 0) {
      toast.warning("No completed documents available to export. Only documents with 'Completed' status can be exported.");
      return;
    }

    setIsBulkExporting(true);
    const schemaContext = schemaSelectedOption?.Id ? ` (${schemaName})` : '';
    toast.info(`Fetching extraction results for ${processedDocuments.length} documents${schemaContext}...`);

    try {
      const documentsWithResults: Array<{ fileName: string, result: any }> = [];
      let successCount = 0;
      let failureCount = 0;

      // Fetch results for each document with progress updates
      for (let i = 0; i < processedDocuments.length; i++) {
        const doc = processedDocuments[i];
        try {
          const response = await httpUtility.get(`/contentprocessor/processed/${doc.process_id}`);
          if (response.data?.result) {
            documentsWithResults.push({
              fileName: doc.processed_file_name.replace(/\.[^/.]+$/, ''), // Remove extension
              result: response.data.result
            });
            successCount++;
          }
        } catch (error) {
          console.error(`Failed to fetch results for ${doc.processed_file_name}:`, error);
          failureCount++;
        }

        // Show progress every 10 documents
        if ((i + 1) % 10 === 0) {
          toast.info(`Progress: ${i + 1}/${processedDocuments.length} documents processed...`);
        }
      }

      if (documentsWithResults.length === 0) {
        toast.error("Failed to fetch any extraction results");
        return;
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const schemaPrefix = schemaSelectedOption?.Id ? `${schemaSelectedOption.Description.replace(/\s+/g, '_')}_` : '';
      const fileName = `${schemaPrefix}BulkExtractionResults_${timestamp}.xlsx`;

      exportBulkResultsToExcel(documentsWithResults, fileName);

      toast.success(
        `Exported ${successCount} document(s)${schemaContext} to Excel${failureCount > 0 ? `. ${failureCount} failed.` : ''}`
      );
    } catch (error) {
      console.error("Bulk export failed:", error);
      toast.error("Failed to export extraction results");
    } finally {
      setIsBulkExporting(false);
    }
  };

  return (
    <div className="panelLeft">
      <PanelToolbar icon={null} header="Processing Queue">
        <Button icon={<ChevronDoubleLeft />} title="Collapse Panel" onClick={() => togglePanel('Left')}>
        </Button>
      </PanelToolbar>
      <div className="topContainer">
        <SchemaDropdown />
        <Button appearance="primary" icon={<ArrowUploadRegular />} onClick={handleImportContent}>
          Import Content
        </Button>
        <UploadFilesModal open={isModalOpen} onClose={() => setIsModalOpen(false)} />
        <Button appearance="outline" onClick={refreshGrid} icon={<ArrowClockwiseRegular />}>
          Refresh
        </Button>
        <Button appearance="outline" onClick={handleExportToExcel} icon={<ArrowDownloadRegular />}>
          Export to Excel
        </Button>
        <Button
          appearance="outline"
          onClick={handleBulkExportAllResults}
          icon={<ArrowDownloadRegular />}
          disabled={isBulkExporting}
          title={store.schemaSelectedOption?.Id ? `Export results for ${store.schemaSelectedOption.Description}` : "Export all results"}>
          {isBulkExporting
            ? "Exporting..."
            : store.schemaSelectedOption?.Id
              ? `Export ${store.schemaSelectedOption.Description}`
              : "Bulk Export All Results"}
        </Button>
      </div>
      <div className="leftcontent">
        <ProcessQueueGrid />
      </div>
    </div>
  );
};

export default PanelLeft;
