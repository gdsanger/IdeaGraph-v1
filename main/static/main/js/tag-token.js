(function (window) {
    const DEFAULT_COLOR_PALETTE = [
        '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e',
        '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1',
        '#8b5cf6', '#a855f7', '#d946ef', '#ec4899', '#f43f5e'
    ];

    function initializeTagTokenBox(elementOrId, config) {
        const element = typeof elementOrId === 'string' ? document.getElementById(elementOrId) : elementOrId;
        if (!element) {
            console.warn('Tag token box element not found:', elementOrId);
            return;
        }

        const options = Object.assign({
            allTags: [],
            selectedTags: [],
            fieldName: 'tags',
            inputPlaceholder: 'Add a tag and press Enter',
            colorPalette: DEFAULT_COLOR_PALETTE,
            hiddenInputContainerId: null
        }, config || {});

        let hiddenContainer = null;
        if (options.hiddenInputContainerId) {
            hiddenContainer = document.getElementById(options.hiddenInputContainerId);
        }

        if (!hiddenContainer) {
            hiddenContainer = document.createElement('div');
            if (options.hiddenInputContainerId) {
                hiddenContainer.id = options.hiddenInputContainerId;
            }
            hiddenContainer.style.display = 'none';
            element.insertAdjacentElement('afterend', hiddenContainer);
        }

        const datalistId = `${element.id || 'tag-token-box'}-suggestions-${Math.random().toString(36).slice(2)}`;
        const datalist = document.createElement('datalist');
        datalist.id = datalistId;
        options.allTags.forEach(tag => {
            if (!tag || !tag.name) {
                return;
            }
            const option = document.createElement('option');
            option.value = tag.name;
            datalist.appendChild(option);
        });
        document.body.appendChild(datalist);

        element.innerHTML = '';
        element.classList.add('tag-token-box');

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'tag-token-input';
        input.placeholder = options.inputPlaceholder;
        input.setAttribute('list', datalistId);
        input.setAttribute('autocomplete', 'off');
        element.appendChild(input);

        const suggestions = (options.allTags || []).map(tag => ({
            id: tag.id,
            name: tag.name,
            color: tag.color,
            nameLower: tag.name ? tag.name.toLowerCase() : ''
        }));

        let paletteIndex = Math.floor(Math.random() * options.colorPalette.length);
        let selected = [];

        function nextColor() {
            const color = options.colorPalette[paletteIndex % options.colorPalette.length];
            paletteIndex += 1;
            return color;
        }

        function syncHiddenInputs() {
            hiddenContainer.innerHTML = '';
            selected.forEach(tag => {
                const hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = options.fieldName;
                hidden.value = tag.isNew ? `new:${tag.name}` : tag.id;
                hiddenContainer.appendChild(hidden);
            });
        }

        function renderTokens() {
            element.querySelectorAll('.tag-token').forEach(token => token.remove());
            selected.forEach(tag => {
                const token = document.createElement('span');
                token.className = 'tag-token badge rounded-pill';
                token.style.backgroundColor = tag.color || '#3b82f6';
                token.title = tag.name;

                const label = document.createElement('span');
                label.textContent = tag.name;
                token.appendChild(label);

                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'tag-token-remove';
                removeBtn.setAttribute('aria-label', `Remove tag ${tag.name}`);
                removeBtn.innerHTML = '&times;';
                removeBtn.addEventListener('click', event => {
                    event.stopPropagation();
                    removeTag(tag.nameLower);
                });

                token.appendChild(removeBtn);
                element.insertBefore(token, input);
            });
            syncHiddenInputs();
        }

        function addTag(tag) {
            if (!tag || !tag.name) {
                return;
            }
            const nameLower = tag.name.toLowerCase();
            if (selected.some(existing => existing.nameLower === nameLower)) {
                return;
            }

            const suggestion = suggestions.find(entry => entry.nameLower === nameLower);
            const resolvedTag = {
                id: tag.id || (suggestion ? suggestion.id : null),
                name: tag.name,
                color: tag.color || (suggestion ? suggestion.color : nextColor()),
                isNew: tag.isNew || !(suggestion && suggestion.id),
                nameLower
            };

            if (resolvedTag.id && resolvedTag.isNew) {
                resolvedTag.isNew = false;
            }

            selected.push(resolvedTag);
            renderTokens();
        }

        function removeTag(nameLower) {
            const index = selected.findIndex(tag => tag.nameLower === nameLower);
            if (index === -1) {
                return;
            }
            selected.splice(index, 1);
            renderTokens();
        }

        function addTagFromValue(value) {
            const trimmed = (value || '').trim();
            if (!trimmed) {
                return;
            }
            addTag({ name: trimmed });
            input.value = '';
        }

        input.addEventListener('keydown', event => {
            if (['Enter', 'Tab', ','].includes(event.key)) {
                event.preventDefault();
                addTagFromValue(input.value);
            } else if (event.key === 'Backspace' && !input.value) {
                const last = selected[selected.length - 1];
                if (last) {
                    removeTag(last.nameLower);
                }
            }
        });

        input.addEventListener('change', () => {
            addTagFromValue(input.value);
        });

        element.addEventListener('click', () => {
            input.focus();
        });

        (options.selectedTags || []).forEach(tag => {
            if (!tag || !tag.name) {
                return;
            }
            addTag({
                id: tag.id,
                name: tag.name,
                color: tag.color,
                isNew: false
            });
        });

        renderTokens();
    }

    window.initializeTagTokenBox = initializeTagTokenBox;
})(window);
