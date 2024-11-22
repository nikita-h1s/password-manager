/* global bootstrap: false */
const initializeTooltips = () => {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
};


// Item information from password list
const setupResourceClickHandlers = () => {
    const resourceItems = document.querySelectorAll('.list-group-item');
    const resourceName = document.querySelector('.resource-name');
    const resourcePassword = document.querySelector('.resource-password');
    const resourceURL = document.querySelector('.resource-url');
    const resourceCreationDate = document.querySelector('.resource-creation-date');
    const resourceModifiedDate = document.querySelector('.resource-modified-date');
    const resourceID = document.querySelector('.resource-id-val');

    const setActiveItem = (clickedItem) => {
        resourceItems.forEach(item =>
            item.classList.remove('list-group-item-active'));

        clickedItem.classList.add('list-group-item-active');
    }

    resourceItems.forEach(item => {
        item.addEventListener('click', (event) => {
            event.preventDefault();

            const resourceId = item.getAttribute('data-id');
            const resource = resources[resourceId];

            setActiveItem(item);

            resourceName.textContent = `${resource.name}`;
            resourcePassword.value = `${resource.password}`;
            resourceURL.value = `${resource.resource_url || 'N/A'}`;
            resourceCreationDate.value = `${resource.resource_creation_date}`;
            resourceModifiedDate.value = `${resource.pass_last_modified_date}`;
            resourceID.value = resourceId;
        });
    });

    if (resourceItems.length > 0) {
        const firstResource = resourceItems[0];
        firstResource.click();
    }
};


const editResourcesInformation = () => {
    document.querySelector('.edit-button').addEventListener('click', function () {
        document.querySelectorAll('.form-control').forEach(input => input.disabled = false);
        document.querySelector('.edit-button').style.display = 'none';
        document.querySelector('.save-button').style.display = 'inline-block';
    });

    document.querySelector('.save-button').addEventListener('click', function () {
        // Assuming you have a form element and the inputs are within the form
        const form = document.querySelector('.resource-form');
        const data = new FormData(form);

        // Submit the form with the updated data
        form.submit(); // This triggers the form's action route in Flask
    });
};


const removeFlashMessages = () => {
    setTimeout(() => {
        const flashMessages = document.getElementById('flash-messages');
        if (flashMessages) {
            flashMessages.remove();
        }
    }, 3000);
}


document.addEventListener('DOMContentLoaded', () => {
    initializeTooltips();
    setupResourceClickHandlers();
    editResourcesInformation();
    removeFlashMessages();
});