(() => {
    const excludedSortHeaders = /\b(action|actions|form|update|enroll|view)\b/i;
    const numericHeaders = /\b(amount|paid|balance|total|units|year|seats|capacity|count|offerings)\b/i;
    const dateHeaders = /\b(date|created|received|enrolled)\b/i;

    const compareCells = (left, right, header) => {
        const leftText = left.cells[header.index]?.textContent.trim() || '';
        const rightText = right.cells[header.index]?.textContent.trim() || '';

        if (dateHeaders.test(header.label)) {
            const leftDate = Date.parse(leftText);
            const rightDate = Date.parse(rightText);
            if (!Number.isNaN(leftDate) && !Number.isNaN(rightDate)) {
                return leftDate - rightDate;
            }
        }

        if (numericHeaders.test(header.label)) {
            const leftNumber = Number.parseFloat(leftText.replace(/[^\d.-]/g, ''));
            const rightNumber = Number.parseFloat(rightText.replace(/[^\d.-]/g, ''));
            if (!Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)) {
                return leftNumber - rightNumber;
            }
        }

        return leftText.localeCompare(rightText, undefined, {
            numeric: true,
            sensitivity: 'base',
        });
    };

    document.querySelectorAll('main table').forEach((table) => {
        const body = table.tBodies[0];
        const headerRow = table.tHead?.rows[0];
        if (!body || !headerRow) return;

        const headers = [...headerRow.cells]
            .map((cell, index) => ({ index, label: cell.textContent.trim() }))
            .filter((header) => header.label && !excludedSortHeaders.test(header.label));
        if (!headers.length) return;

        const controls = document.createElement('div');
        controls.className = 'table-tools';
        controls.setAttribute('role', 'group');
        controls.setAttribute('aria-label', 'Table search, sorting, and pagination');

        const searchLabel = document.createElement('label');
        searchLabel.className = 'table-tools-search';
        const searchText = document.createElement('span');
        searchText.textContent = 'Search';
        const searchInput = document.createElement('input');
        searchInput.type = 'search';
        searchInput.placeholder = 'Search this table';
        searchInput.setAttribute('aria-label', `Search ${headers.map((header) => header.label).join(', ')}`);
        searchLabel.append(searchText, searchInput);

        const sortLabel = document.createElement('label');
        sortLabel.className = 'table-tools-sort';
        const sortText = document.createElement('span');
        sortText.textContent = 'Sort by';
        const sortSelect = document.createElement('select');
        sortSelect.setAttribute('aria-label', 'Sort table by');
        const originalOrder = document.createElement('option');
        originalOrder.value = '';
        originalOrder.textContent = 'Default order';
        sortSelect.append(originalOrder);
        headers.forEach((header) => {
            const option = document.createElement('option');
            option.value = String(header.index);
            option.textContent = header.label;
            sortSelect.append(option);
        });
        sortLabel.append(sortText, sortSelect);

        const directionButton = document.createElement('button');
        directionButton.className = 'table-tools-direction';
        directionButton.type = 'button';
        directionButton.textContent = 'Ascending';
        directionButton.setAttribute('aria-label', 'Change sort direction');

        const pageSizeLabel = document.createElement('label');
        pageSizeLabel.className = 'table-tools-page-size';
        const pageSizeText = document.createElement('span');
        pageSizeText.textContent = 'Rows per page';
        const pageSizeSelect = document.createElement('select');
        pageSizeSelect.setAttribute('aria-label', 'Rows per page');
        [10, 25, 50].forEach((size) => {
            const option = document.createElement('option');
            option.value = String(size);
            option.textContent = String(size);
            pageSizeSelect.append(option);
        });
        pageSizeSelect.value = '10';
        pageSizeLabel.append(pageSizeText, pageSizeSelect);

        const count = document.createElement('span');
        count.className = 'table-tools-count';
        count.setAttribute('aria-live', 'polite');

        const pagination = document.createElement('div');
        pagination.className = 'table-tools-pagination';
        const previousButton = document.createElement('button');
        previousButton.type = 'button';
        previousButton.textContent = 'Previous';
        previousButton.setAttribute('aria-label', 'Previous table page');
        const pageStatus = document.createElement('span');
        pageStatus.setAttribute('aria-live', 'polite');
        const nextButton = document.createElement('button');
        nextButton.type = 'button';
        nextButton.textContent = 'Next';
        nextButton.setAttribute('aria-label', 'Next table page');
        pagination.append(previousButton, pageStatus, nextButton);
        controls.append(searchLabel, sortLabel, directionButton, pageSizeLabel, count, pagination);
        table.before(controls);

        const allRows = [...body.rows].filter((row) => (
            row.cells.length === headerRow.cells.length
            && ![...row.cells].some((cell) => cell.colSpan > 1)
        ));
        const placeholderRows = [...body.rows].filter((row) => (
            [...row.cells].some((cell) => cell.colSpan > 1)
        ));
        const initialPositions = new Map(allRows.map((row, index) => [row, index]));
        let currentPage = 1;
        let descending = false;
        let noResultsRow = null;

        const render = () => {
            const query = searchInput.value.trim().toLocaleLowerCase();
            let visibleRows = allRows.filter((row) => (
                row.textContent.toLocaleLowerCase().includes(query)
            ));

            const sortIndex = Number.parseInt(sortSelect.value, 10);
            const selectedHeader = headers.find((header) => header.index === sortIndex);
            if (selectedHeader) {
                visibleRows.sort((left, right) => (
                    compareCells(left, right, selectedHeader) * (descending ? -1 : 1)
                ));
            } else {
                visibleRows.sort((left, right) => initialPositions.get(left) - initialPositions.get(right));
            }

            const pageSize = Number.parseInt(pageSizeSelect.value, 10);
            const pageCount = Math.max(1, Math.ceil(visibleRows.length / pageSize));
            currentPage = Math.min(currentPage, pageCount);
            const start = (currentPage - 1) * pageSize;
            const pageRows = new Set(visibleRows.slice(start, start + pageSize));

            placeholderRows.forEach((row) => {
                row.hidden = Boolean(query);
            });
            visibleRows.forEach((row) => {
                row.hidden = !pageRows.has(row);
                body.append(row);
            });
            allRows.filter((row) => !pageRows.has(row)).forEach((row) => {
                row.hidden = true;
            });

            if (noResultsRow) noResultsRow.remove();
            if (query && visibleRows.length === 0) {
                noResultsRow = body.insertRow();
                noResultsRow.className = 'table-tools-no-results';
                const message = noResultsRow.insertCell();
                message.colSpan = headerRow.cells.length;
                message.textContent = 'No matching records found.';
            }

            count.textContent = visibleRows.length
                ? `Showing ${start + 1}-${Math.min(start + pageSize, visibleRows.length)} of ${visibleRows.length}`
                : `${visibleRows.length} records`;
            pageStatus.textContent = `Page ${currentPage} of ${pageCount}`;
            previousButton.disabled = currentPage <= 1;
            nextButton.disabled = currentPage >= pageCount;
        };

        searchInput.addEventListener('input', () => {
            currentPage = 1;
            render();
        });
        sortSelect.addEventListener('change', () => {
            currentPage = 1;
            render();
        });
        directionButton.addEventListener('click', () => {
            descending = !descending;
            directionButton.textContent = descending ? 'Descending' : 'Ascending';
            render();
        });
        pageSizeSelect.addEventListener('change', () => {
            currentPage = 1;
            render();
        });
        previousButton.addEventListener('click', () => {
            currentPage -= 1;
            render();
        });
        nextButton.addEventListener('click', () => {
            currentPage += 1;
            render();
        });
        render();
    });
})();
