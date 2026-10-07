document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-facility-combobox]').forEach((root) => {
    const select = root.querySelector('select[name="facility"]');
    const control = root.querySelector('.combo-control');
    const input = control.querySelector('[role="combobox"]');
    const toggle = control.querySelector('.combo-toggle');
    const list = control.querySelector('[role="listbox"]');
    const label = root.querySelector('label');
    const choices = [...select.options].filter((option) => option.value).map((option) => ({
      value: option.value,
      label: option.textContent.trim(),
    }));
    let visible = choices;
    let active = -1;

    const close = () => {
      list.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      toggle.setAttribute('aria-expanded', 'false');
      active = -1;
    };

    const highlight = (index) => {
      active = index;
      input.setAttribute('aria-activedescendant', `facility-option-${index}`);
      [...list.querySelectorAll('[role="option"]')].forEach((option, i) => {
        option.classList.toggle('active', i === active);
        option.setAttribute('aria-selected', i === active ? 'true' : 'false');
        if (i === active) option.scrollIntoView({ block: 'nearest' });
      });
    };

    const choose = (choice) => {
      select.value = choice.value;
      input.value = choice.label;
      input.setCustomValidity('');
      input.focus();
      close();
    };

    const render = (query = '') => {
      visible = choices.filter((choice) => choice.label.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
      list.replaceChildren();
      visible.forEach((choice, index) => {
        const option = document.createElement('button');
        option.type = 'button';
        option.id = `facility-option-${index}`;
        option.className = 'combo-option';
        option.setAttribute('role', 'option');
        option.setAttribute('aria-selected', 'false');
        option.textContent = choice.label;
        option.addEventListener('mousedown', (event) => event.preventDefault());
        option.addEventListener('click', () => choose(choice));
        list.append(option);
      });
      if (!visible.length) {
        const empty = document.createElement('p');
        empty.className = 'combo-empty';
        empty.textContent = root.dataset.noResults;
        list.append(empty);
      }
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-expanded', 'true');
      input.removeAttribute('aria-activedescendant');
      active = -1;
    };

    const selected = choices.find((choice) => choice.value === select.value);
    if (selected) input.value = selected.label;
    select.required = false;
    select.hidden = true;
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');
    control.hidden = false;
    label.htmlFor = input.id;

    input.addEventListener('focus', () => { if (list.hidden) render(''); });
    input.addEventListener('input', () => {
      select.value = '';
      input.setCustomValidity('');
      render(input.value);
    });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') { close(); return; }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        if (list.hidden) render('');
        if (visible.length) highlight((active + (event.key === 'ArrowDown' ? 1 : -1) + visible.length) % visible.length);
      }
      if (event.key === 'Enter' && !list.hidden) {
        event.preventDefault();
        if (active >= 0) choose(visible[active]);
        else if (visible.length === 1) choose(visible[0]);
      }
    });
    toggle.addEventListener('click', () => {
      if (list.hidden) { render(''); input.focus(); }
      else close();
    });
    root.addEventListener('focusout', () => {
      requestAnimationFrame(() => { if (!root.contains(document.activeElement)) close(); });
    });
    document.addEventListener('click', (event) => { if (!root.contains(event.target)) close(); });
    root.closest('form').addEventListener('submit', (event) => {
      if (!select.value) {
        input.setCustomValidity(root.dataset.invalidChoice);
        input.reportValidity();
        input.focus();
        event.preventDefault();
      }
    });
  });
});
